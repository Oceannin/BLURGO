"""Reproducible OBS runtime smoke test for BlurGo.

OBS WebSocket must be enabled. The script creates isolated QA scenes and sources,
captures source screenshots, validates filter lifecycle behavior, and writes a
machine-readable report plus PNG evidence.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import struct
import time
import uuid
import zlib
from pathlib import Path
from typing import Any

import websockets


class ObsRequestError(RuntimeError):
    """Raised when OBS WebSocket rejects a request."""


class ObsClient:
    def __init__(self, url: str, password: str | None) -> None:
        self.url = url
        self.password = password
        self.socket: Any = None

    async def __aenter__(self) -> "ObsClient":
        self.socket = await websockets.connect(self.url, max_size=32 * 1024 * 1024)
        hello = json.loads(await self.socket.recv())
        if hello.get("op") != 0:
            raise RuntimeError(f"Unexpected OBS hello: {hello}")

        identify: dict[str, Any] = {"rpcVersion": 1, "eventSubscriptions": 0}
        authentication = hello.get("d", {}).get("authentication")
        if authentication:
            if self.password is None:
                raise RuntimeError("OBS WebSocket requires --password")
            secret = base64.b64encode(
                hashlib.sha256((self.password + authentication["salt"]).encode()).digest()
            ).decode()
            identify["authentication"] = base64.b64encode(
                hashlib.sha256((secret + authentication["challenge"]).encode()).digest()
            ).decode()

        await self.socket.send(json.dumps({"op": 1, "d": identify}))
        identified = json.loads(await self.socket.recv())
        if identified.get("op") != 2:
            raise RuntimeError(f"OBS WebSocket identification failed: {identified}")
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.socket.close()

    async def request(
        self, request_type: str, request_data: dict[str, Any] | None = None, *, allow_failure: bool = False
    ) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        await self.socket.send(
            json.dumps(
                {
                    "op": 6,
                    "d": {
                        "requestType": request_type,
                        "requestId": request_id,
                        "requestData": request_data or {},
                    },
                }
            )
        )

        while True:
            message = json.loads(await self.socket.recv())
            if message.get("op") != 7 or message.get("d", {}).get("requestId") != request_id:
                continue
            status = message["d"]["requestStatus"]
            if not status.get("result"):
                if allow_failure:
                    return {"requestStatus": status}
                raise ObsRequestError(f"{request_type}: {status}")
            return message["d"].get("responseData", {})


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


def pattern_pixel(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
    border = max(24, min(width, height) // 16)
    if x < border or y < border or x >= width - border or y >= height - border:
        return 0, 0, 0, 0

    block = max(16, min(width, height) // 15)
    base = (246, 248, 252) if ((x // block) + (y // block)) % 2 == 0 else (15, 23, 42)
    nx = (x - width / 2.0) / max(1.0, width * 0.24)
    ny = (y - height / 2.0) / max(1.0, height * 0.40)
    if nx * nx + ny * ny <= 1.0:
        base = (239, 68, 68)
    if abs(x - width / 2.0) < width * 0.075 and abs(y - height / 2.0) < height * 0.14:
        base = (37, 99, 235)
    return *base, 255


def write_pattern_png(path: Path, width: int, height: int) -> None:
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows.extend(pattern_pixel(x, y, width, height))
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(signature + png_chunk(b"IHDR", ihdr) + png_chunk(b"IDAT", zlib.compress(rows, 6)) + png_chunk(b"IEND", b""))


def paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    diagonal_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= diagonal_distance:
        return left
    if up_distance <= diagonal_distance:
        return up
    return upper_left


def read_png(path: Path) -> tuple[int, int, int, bytes]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"Not a PNG: {path}")

    offset = 8
    compressed = bytearray()
    width = height = color_type = 0
    while offset < len(data):
        size = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + size]
        offset += 12 + size
        if kind == b"IHDR":
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if bit_depth != 8 or color_type not in (2, 6) or compression or filtering or interlace:
                raise RuntimeError(f"Unsupported PNG format in {path}")
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break

    channels = 4 if color_type == 6 else 3
    raw = zlib.decompress(compressed)
    stride = width * channels
    pixels = bytearray(height * stride)
    previous = bytearray(stride)
    source_offset = 0
    for y in range(height):
        filter_type = raw[source_offset]
        source_offset += 1
        current = bytearray(raw[source_offset : source_offset + stride])
        source_offset += stride
        for x in range(stride):
            left = current[x - channels] if x >= channels else 0
            up = previous[x]
            upper_left = previous[x - channels] if x >= channels else 0
            if filter_type == 1:
                current[x] = (current[x] + left) & 0xFF
            elif filter_type == 2:
                current[x] = (current[x] + up) & 0xFF
            elif filter_type == 3:
                current[x] = (current[x] + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                current[x] = (current[x] + paeth(left, up, upper_left)) & 0xFF
            elif filter_type != 0:
                raise RuntimeError(f"Unsupported PNG filter {filter_type} in {path}")
        pixels[y * stride : (y + 1) * stride] = current
        previous = current
    return width, height, channels, bytes(pixels)


def compare_png(reference: Path, candidate: Path) -> dict[str, float | int | str]:
    width, height, channels, left = read_png(reference)
    other_width, other_height, other_channels, right = read_png(candidate)
    if (width, height, channels) != (other_width, other_height, other_channels):
        raise RuntimeError(f"PNG dimensions differ: {reference} vs {candidate}")

    rgb_channels = min(3, channels)
    total = 0
    black_pixels = 0
    transparent_pixels = 0
    low_alpha_pixels = 0
    alpha_total = 0
    alpha_min = 255
    alpha_max = 255 if channels != 4 else 0
    for index in range(0, len(left), channels):
        total += sum(abs(left[index + channel] - right[index + channel]) for channel in range(rgb_channels))
        if max(right[index : index + rgb_channels]) <= 2:
            black_pixels += 1
        if channels == 4:
            alpha = right[index + 3]
            alpha_total += alpha
            alpha_min = min(alpha_min, alpha)
            alpha_max = max(alpha_max, alpha)
            if alpha == 0:
                transparent_pixels += 1
            if alpha <= 8:
                low_alpha_pixels += 1

    pixel_count = width * height
    return {
        "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "mean_absolute_rgb_difference": round(total / (pixel_count * rgb_channels), 4),
        "black_pixel_ratio": round(black_pixels / pixel_count, 6),
        "transparent_pixel_ratio": round(transparent_pixels / pixel_count, 6),
        "low_alpha_pixel_ratio": round(low_alpha_pixels / pixel_count, 6),
        "alpha_min": alpha_min,
        "alpha_max": alpha_max,
        "alpha_mean": round(alpha_total / pixel_count, 4) if channels == 4 else 255.0,
    }


async def save_screenshot(client: ObsClient, source_name: str, path: Path, width: int, height: int) -> None:
    response = await client.request(
        "GetSourceScreenshot",
        {
            "sourceName": source_name,
            "imageFormat": "png",
            "imageWidth": width,
            "imageHeight": height,
            "imageCompressionQuality": -1,
        },
    )
    path.write_bytes(base64.b64decode(response["imageData"].split(",", 1)[1]))


async def sample_stats(client: ObsClient, seconds: float) -> dict[str, float]:
    samples: list[dict[str, float]] = []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        samples.append(await client.request("GetStats"))
        await asyncio.sleep(0.25)
    return {
        "samples": float(len(samples)),
        "average_frame_render_time_ms": round(
            sum(sample["averageFrameRenderTime"] for sample in samples) / max(1, len(samples)), 4
        ),
        "cpu_usage_percent": round(sum(sample["cpuUsage"] for sample in samples) / max(1, len(samples)), 4),
        "memory_usage_mb": round(sum(sample["memoryUsage"] for sample in samples) / max(1, len(samples)), 4),
        "render_skipped_frames": float(samples[-1]["renderSkippedFrames"] if samples else 0),
    }


async def stress_scene_switches(
    client: ObsClient, scene: str, wrapper: str, seconds: float, interval: float
) -> dict[str, Any] | None:
    if seconds <= 0.0:
        return None

    started = time.monotonic()
    deadline = started + seconds
    samples: list[dict[str, float]] = []
    switches = 0
    sample_every = max(1, round(2.0 / interval))
    while time.monotonic() < deadline:
        await client.request(
            "SetCurrentProgramScene", {"sceneName": wrapper if switches % 2 else scene}
        )
        switches += 1
        await asyncio.sleep(interval)
        if switches % sample_every == 0:
            stats = await client.request("GetStats")
            samples.append(
                {
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "memory_usage_mb": stats["memoryUsage"],
                    "average_frame_render_time_ms": stats["averageFrameRenderTime"],
                    "render_skipped_frames": stats["renderSkippedFrames"],
                }
            )

    await client.request("SetCurrentProgramScene", {"sceneName": wrapper})
    if not samples:
        return {"seconds": seconds, "switches": switches, "samples": 0}

    x_mean = sum(sample["elapsed_seconds"] for sample in samples) / len(samples)
    y_mean = sum(sample["memory_usage_mb"] for sample in samples) / len(samples)
    denominator = sum((sample["elapsed_seconds"] - x_mean) ** 2 for sample in samples)
    slope_per_second = (
        sum(
            (sample["elapsed_seconds"] - x_mean) * (sample["memory_usage_mb"] - y_mean)
            for sample in samples
        )
        / denominator
        if denominator
        else 0.0
    )
    return {
        "seconds": round(time.monotonic() - started, 3),
        "switches": switches,
        "samples": len(samples),
        "memory_first_mb": round(samples[0]["memory_usage_mb"], 4),
        "memory_last_mb": round(samples[-1]["memory_usage_mb"], 4),
        "memory_min_mb": round(min(sample["memory_usage_mb"] for sample in samples), 4),
        "memory_max_mb": round(max(sample["memory_usage_mb"] for sample in samples), 4),
        "memory_slope_mb_per_minute": round(slope_per_second * 60.0, 6),
        "render_skipped_frames_start": samples[0]["render_skipped_frames"],
        "render_skipped_frames_end": samples[-1]["render_skipped_frames"],
        "max_frame_render_time_ms": round(
            max(sample["average_frame_render_time_ms"] for sample in samples), 4
        ),
    }


async def test_display_capture(
    client: ObsClient, output: Path, run_id: str, width: int, height: int
) -> dict[str, Any]:
    kinds = (await client.request("GetInputKindList"))["inputKinds"]
    candidates = [kind for kind in kinds if kind.startswith("monitor_capture")]
    if not candidates:
        return {"status": "skipped", "reason": "No monitor capture input kind is available"}

    scene = f"BlurGo Display QA {run_id}"
    source = f"BlurGo Display Capture {run_id}"
    filter_name = "BlurGo Display QA"
    evidence_files: list[Path] = []
    previous_scene = (await client.request("GetCurrentProgramScene"))["currentProgramSceneName"]
    await client.request("CreateScene", {"sceneName": scene})
    try:
        await client.request(
            "CreateInput",
            {
                "sceneName": scene,
                "inputName": source,
                "inputKind": candidates[0],
                "inputSettings": {},
                "sceneItemEnabled": True,
            },
        )
        monitor_selection = "default"
        for property_name in ("monitor_id", "monitor"):
            property_response = await client.request(
                "GetInputPropertiesListPropertyItems",
                {"inputName": source, "propertyName": property_name},
                allow_failure=True,
            )
            property_items = property_response.get("propertyItems", [])
            available_items = [
                item
                for item in property_items
                if item.get("itemEnabled", True) and item.get("itemValue") not in (None, "")
            ]
            if not available_items:
                continue
            await client.request(
                "SetInputSettings",
                {
                    "inputName": source,
                    "inputSettings": {property_name: available_items[0]["itemValue"]},
                    "overlay": True,
                },
            )
            monitor_selection = f"first_available_{property_name}"
            break
        await client.request("SetCurrentProgramScene", {"sceneName": scene})
        await asyncio.sleep(0.75)
        baseline = output / "private-display-baseline.png"
        evidence_files.append(baseline)
        await save_screenshot(client, source, baseline, width, height)
        baseline_metrics = compare_png(baseline, baseline)
        if baseline_metrics["black_pixel_ratio"] > 0.98:
            return {
                "status": "skipped",
                "input_kind": candidates[0],
                "monitor_selection": monitor_selection,
                "reason": "Selected monitor capture produced an almost entirely black frame",
            }

        await client.request(
            "CreateSourceFilter",
            {
                "sourceName": source,
                "filterName": filter_name,
                "filterKind": "blurgo_filter",
                "filterSettings": {
                    "mode": 0,
                    "radius": 12.0,
                    "passes": 2,
                    "pixel_size": 20.0,
                    "mix": 100.0,
                },
            },
        )
        results: dict[str, dict[str, float | int | str]] = {}
        for mode, name in ((0, "gaussian"), (1, "box"), (2, "pixelate")):
            await client.request(
                "SetSourceFilterSettings",
                {
                    "sourceName": source,
                    "filterName": filter_name,
                    "filterSettings": {"mode": mode},
                    "overlay": True,
                },
            )
            await asyncio.sleep(0.2)
            candidate = output / f"private-display-{name}.png"
            evidence_files.append(candidate)
            await save_screenshot(client, source, candidate, width, height)
            results[name] = compare_png(baseline, candidate)
            if results[name]["mean_absolute_rgb_difference"] <= 0.05:
                raise RuntimeError(f"Display capture {name} did not materially change the frame")
        return {
            "status": "passed",
            "input_kind": candidates[0],
            "monitor_selection": monitor_selection,
            "results": results,
        }
    finally:
        await client.request(
            "SetCurrentProgramScene", {"sceneName": previous_scene}, allow_failure=True
        )
        await client.request("RemoveInput", {"inputName": source}, allow_failure=True)
        await client.request("RemoveScene", {"sceneName": scene}, allow_failure=True)
        for path in evidence_files:
            path.unlink(missing_ok=True)


async def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    pattern = output / "pattern.png"
    resized_pattern = output / "pattern-small.png"
    write_pattern_png(pattern, args.width, args.height)
    write_pattern_png(resized_pattern, max(64, args.width // 2), max(64, args.height // 2))

    run_id = uuid.uuid4().hex[:8]
    scene = f"BlurGo QA {run_id}"
    wrapper = f"BlurGo QA Wrapper {run_id}"
    input_name = f"BlurGo QA Pattern {run_id}"
    source_filter = "BlurGo Source QA"
    scene_filter = "BlurGo Scene QA"

    async with ObsClient(args.url, args.password) as client:
        version_response = await client.request("GetVersion")
        version = {
            key: version_response[key]
            for key in (
                "obsVersion",
                "obsWebSocketVersion",
                "platform",
                "platformDescription",
                "rpcVersion",
            )
        }
        video_before = await client.request("GetVideoSettings")
        if args.set_video_settings:
            await client.request(
                "SetVideoSettings",
                {
                    "baseWidth": args.width,
                    "baseHeight": args.height,
                    "outputWidth": args.width,
                    "outputHeight": args.height,
                    "fpsNumerator": args.fps,
                    "fpsDenominator": 1,
                },
            )
        video_during_test = await client.request("GetVideoSettings")
        await client.request("CreateScene", {"sceneName": scene})
        await client.request("CreateScene", {"sceneName": wrapper})
        await client.request(
            "CreateInput",
            {
                "sceneName": scene,
                "inputName": input_name,
                "inputKind": "image_source",
                "inputSettings": {"file": str(pattern), "unload": False},
                "sceneItemEnabled": True,
            },
        )
        await client.request("CreateSceneItem", {"sceneName": wrapper, "sourceName": scene, "sceneItemEnabled": True})
        await client.request("SetCurrentProgramScene", {"sceneName": scene})
        await asyncio.sleep(0.5)

        original = output / "source-original.png"
        await save_screenshot(client, input_name, original, args.width, args.height)
        await client.request(
            "CreateSourceFilter",
            {
                "sourceName": input_name,
                "filterName": source_filter,
                "filterKind": "blurgo_filter",
                "filterSettings": {
                    "mode": 0,
                    "radius": 18.0,
                    "passes": 3,
                    "pixel_size": 24.0,
                    "mix": 100.0,
                },
            },
        )

        render_results: dict[str, dict[str, float | int | str]] = {}
        for mode, name in ((0, "gaussian"), (1, "box"), (2, "pixelate")):
            await client.request(
                "SetSourceFilterSettings",
                {
                    "sourceName": input_name,
                    "filterName": source_filter,
                    "filterSettings": {"mode": mode},
                    "overlay": True,
                },
            )
            await asyncio.sleep(0.2)
            candidate = output / f"source-{name}.png"
            await save_screenshot(client, input_name, candidate, args.width, args.height)
            render_results[name] = compare_png(original, candidate)
            if render_results[name]["mean_absolute_rgb_difference"] <= 0.05:
                raise RuntimeError(f"{name} did not materially change the source")
            if (
                render_results[name]["alpha_min"] > 8
                or render_results[name]["alpha_max"] < 247
                or render_results[name]["low_alpha_pixel_ratio"] <= 0.0005
            ):
                raise RuntimeError(f"{name} did not preserve a meaningful alpha range")

        for settings, name in (
            ({"mode": 0, "radius": 18.0, "mix": 0.0}, "mix-zero"),
            ({"mode": 0, "radius": 0.0, "mix": 100.0}, "radius-zero"),
        ):
            await client.request(
                "SetSourceFilterSettings",
                {
                    "sourceName": input_name,
                    "filterName": source_filter,
                    "filterSettings": settings,
                    "overlay": True,
                },
            )
            await asyncio.sleep(0.2)
            passthrough = output / f"source-{name}.png"
            await save_screenshot(client, input_name, passthrough, args.width, args.height)
            result = compare_png(original, passthrough)
            render_results[name] = result
            if result["mean_absolute_rgb_difference"] > 0.05:
                raise RuntimeError(f"{name} was not a visual passthrough")

        await client.request(
            "SetSourceFilterSettings",
            {
                "sourceName": input_name,
                "filterName": source_filter,
                "filterSettings": {"mode": 0, "radius": 12.0, "passes": 2, "mix": 100.0},
                "overlay": True,
            },
        )
        await client.request(
            "CreateSourceFilter",
            {
                "sourceName": input_name,
                "filterName": "BlurGo Reorder QA",
                "filterKind": "blurgo_filter",
                "filterSettings": {"mode": 2, "pixel_size": 8.0, "mix": 100.0},
            },
        )
        await client.request(
            "SetSourceFilterIndex",
            {"sourceName": input_name, "filterName": "BlurGo Reorder QA", "filterIndex": 0},
        )
        reordered = await client.request("GetSourceFilterList", {"sourceName": input_name})
        if reordered["filters"][0]["filterName"] != "BlurGo Reorder QA":
            raise RuntimeError("Filter reorder did not persist")
        await client.request(
            "RemoveSourceFilter", {"sourceName": input_name, "filterName": "BlurGo Reorder QA"}
        )

        await client.request(
            "SetInputSettings",
            {
                "inputName": input_name,
                "inputSettings": {"file": str(resized_pattern), "unload": False},
                "overlay": True,
            },
        )
        await asyncio.sleep(0.2)
        resized = output / "source-resized.png"
        await save_screenshot(client, input_name, resized, args.width, args.height)
        resized_result = compare_png(original, resized)
        if resized_result["mean_absolute_rgb_difference"] <= 0.05:
            raise RuntimeError("Source resize did not change the rendered output")
        await client.request(
            "SetInputSettings",
            {
                "inputName": input_name,
                "inputSettings": {"file": str(pattern), "unload": False},
                "overlay": True,
            },
        )

        await client.request(
            "RemoveSourceFilter", {"sourceName": input_name, "filterName": source_filter}
        )
        scene_original = output / "scene-original.png"
        await save_screenshot(client, scene, scene_original, args.width, args.height)
        await client.request(
            "CreateSourceFilter",
            {
                "sourceName": scene,
                "filterName": scene_filter,
                "filterKind": "blurgo_filter",
                "filterSettings": {"mode": 0, "radius": 12.0, "passes": 2, "pixel_size": 16.0, "mix": 100.0},
            },
        )
        await asyncio.sleep(0.2)
        scene_blur = output / "scene-gaussian.png"
        await save_screenshot(client, scene, scene_blur, args.width, args.height)
        scene_result = compare_png(scene_original, scene_blur)
        if scene_result["mean_absolute_rgb_difference"] <= 0.05:
            raise RuntimeError("Scene filter did not materially change the composite")

        await client.request(
            "SetSourceFilterEnabled",
            {"sourceName": scene, "filterName": scene_filter, "filterEnabled": False},
        )
        baseline_stats = await sample_stats(client, args.stats_seconds)
        await client.request(
            "SetSourceFilterEnabled",
            {"sourceName": scene, "filterName": scene_filter, "filterEnabled": True},
        )
        filtered_stats = await sample_stats(client, args.stats_seconds)

        for index in range(args.scene_switches):
            await client.request(
                "SetCurrentProgramScene", {"sceneName": wrapper if index % 2 else scene}
            )
            await asyncio.sleep(0.1)
        await client.request("SetCurrentProgramScene", {"sceneName": wrapper})
        stress = await stress_scene_switches(
            client, scene, wrapper, args.stress_seconds, args.switch_interval
        )
        display_capture = (
            await test_display_capture(client, output, run_id, args.width, args.height)
            if args.test_display_capture
            else {"status": "not_requested"}
        )

        persistence = await client.request("GetSourceFilterList", {"sourceName": scene})

        disposable = f"BlurGo Disposable {run_id}"
        await client.request(
            "CreateInput",
            {
                "sceneName": scene,
                "inputName": disposable,
                "inputKind": "image_source",
                "inputSettings": {"file": str(pattern), "unload": False},
                "sceneItemEnabled": True,
            },
        )
        await client.request(
            "CreateSourceFilter",
            {
                "sourceName": disposable,
                "filterName": "BlurGo Disposable QA",
                "filterKind": "blurgo_filter",
                "filterSettings": {"mode": 0, "radius": 8.0, "passes": 1, "mix": 100.0},
            },
        )
        disposable_render = output / "source-before-delete.png"
        await save_screenshot(client, disposable, disposable_render, 640, 360)
        await client.request("RemoveInput", {"inputName": disposable})

        stats = await client.request("GetStats")
        return {
            "status": "passed",
            "obs_version": version,
            "width": args.width,
            "height": args.height,
            "video_settings_before": video_before,
            "video_settings_during_test": video_during_test,
            "scene": scene,
            "wrapper_scene": wrapper,
            "input": input_name,
            "scene_filter": scene_filter,
            "render_results": render_results,
            "resize_result": resized_result,
            "scene_result": scene_result,
            "filter_state_before_restart": persistence["filters"],
            "performance": {"baseline": baseline_stats, "filtered": filtered_stats},
            "stress": stress,
            "display_capture": display_capture,
            "final_stats": stats,
        }


async def verify_persistence(args: argparse.Namespace) -> dict[str, Any]:
    report = json.loads(args.report.read_text(encoding="utf-8"))
    async with ObsClient(args.url, args.password) as client:
        filters = await client.request("GetSourceFilterList", {"sourceName": report["scene"]})
        match = next(
            (item for item in filters["filters"] if item["filterName"] == report["scene_filter"]), None
        )
        if match is None:
            raise RuntimeError("BlurGo scene filter did not persist after OBS restart")
        expected = report["filter_state_before_restart"][0]["filterSettings"]
        if match["filterSettings"] != expected:
            raise RuntimeError(
                f"Persisted settings differ: expected {expected}, received {match['filterSettings']}"
            )
        return {"status": "passed", "persisted_filter": match}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "verify-persistence"))
    parser.add_argument("--url", default="ws://127.0.0.1:4455")
    parser.add_argument("--password")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/obs-smoke"))
    parser.add_argument("--report", type=Path, default=Path("artifacts/obs-smoke/report.json"))
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--stats-seconds", type=float, default=3.0)
    parser.add_argument("--scene-switches", type=int, default=20)
    parser.add_argument("--set-video-settings", action="store_true")
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--stress-seconds", type=float, default=0.0)
    parser.add_argument("--switch-interval", type=float, default=0.25)
    parser.add_argument(
        "--test-display-capture",
        action="store_true",
        help="Capture the first available monitor locally, validate all modes, then delete private screenshots",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.width < 64 or args.height < 64:
        raise SystemExit("--width and --height must both be at least 64")
    if args.fps < 1 or args.switch_interval <= 0.0 or args.stress_seconds < 0.0:
        raise SystemExit("--fps and --switch-interval must be positive; --stress-seconds cannot be negative")
    result = asyncio.run(run_smoke(args) if args.command == "run" else verify_persistence(args))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = args.output_dir / ("report.json" if args.command == "run" else "persistence.json")
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
