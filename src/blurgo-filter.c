/*
BlurGo for OBS
Copyright (C) 2026 BlurGo contributors

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
*/

#include "blurgo-settings.h"

#include <graphics/vec2.h>
#include <graphics/vec4.h>
#include <obs-module.h>

#define SETTING_MODE "mode"
#define SETTING_RADIUS "radius"
#define SETTING_PASSES "passes"
#define SETTING_PIXEL_SIZE "pixel_size"
#define SETTING_MIX "mix"

struct blurgo_filter_data {
	obs_source_t *context;
	struct blurgo_settings settings;

	gs_effect_t *blur_effect;
	gs_effect_t *composite_effect;
	gs_texrender_t *input;
	gs_texrender_t *ping;
	gs_texrender_t *pong;

	gs_eparam_t *blur_image;
	gs_eparam_t *blur_direction;
	gs_eparam_t *blur_texture_size;
	gs_eparam_t *blur_pixel_size;
	gs_eparam_t *composite_image;
	gs_eparam_t *composite_original;
	gs_eparam_t *composite_mix;
};

static const char *blurgo_filter_get_name(void *unused)
{
	UNUSED_PARAMETER(unused);
	return obs_module_text("BlurGo.FilterName");
}

static gs_effect_t *load_effect(const char *name)
{
	char *path = obs_module_file(name);
	char *error = NULL;
	gs_effect_t *effect = gs_effect_create_from_file(path, &error);

	if (!effect)
		blog(LOG_ERROR, "[BlurGo] Failed to load %s: %s", path, error ? error : "unknown shader error");

	bfree(error);
	bfree(path);
	return effect;
}

static void destroy_graphics_resources(struct blurgo_filter_data *filter)
{
	gs_effect_destroy(filter->blur_effect);
	gs_effect_destroy(filter->composite_effect);
	gs_texrender_destroy(filter->input);
	gs_texrender_destroy(filter->ping);
	gs_texrender_destroy(filter->pong);
}

static void blurgo_filter_destroy(void *data)
{
	struct blurgo_filter_data *filter = data;
	if (!filter)
		return;

	obs_enter_graphics();
	destroy_graphics_resources(filter);
	obs_leave_graphics();
	bfree(filter);
}

static void blurgo_filter_update(void *data, obs_data_t *settings)
{
	struct blurgo_filter_data *filter = data;
	filter->settings.mode = (enum blurgo_mode)obs_data_get_int(settings, SETTING_MODE);
	filter->settings.radius = (float)obs_data_get_double(settings, SETTING_RADIUS);
	filter->settings.passes = (int)obs_data_get_int(settings, SETTING_PASSES);
	filter->settings.pixel_size = (float)obs_data_get_double(settings, SETTING_PIXEL_SIZE);
	filter->settings.mix = (float)(obs_data_get_double(settings, SETTING_MIX) / 100.0);
	blurgo_settings_normalize(&filter->settings);
}

static void *blurgo_filter_create(obs_data_t *settings, obs_source_t *context)
{
	struct blurgo_filter_data *filter = bzalloc(sizeof(*filter));
	filter->context = context;

	obs_enter_graphics();
	filter->blur_effect = load_effect("blurgo-blur.effect");
	filter->composite_effect = load_effect("blurgo-composite.effect");
	filter->input = gs_texrender_create(GS_RGBA, GS_ZS_NONE);
	filter->ping = gs_texrender_create(GS_RGBA, GS_ZS_NONE);
	filter->pong = gs_texrender_create(GS_RGBA, GS_ZS_NONE);
	obs_leave_graphics();

	if (!filter->blur_effect || !filter->composite_effect || !filter->input || !filter->ping || !filter->pong) {
		blog(LOG_ERROR, "[BlurGo] GPU resources could not be initialized; the filter was not created");
		blurgo_filter_destroy(filter);
		return NULL;
	}

	filter->blur_image = gs_effect_get_param_by_name(filter->blur_effect, "image");
	filter->blur_direction = gs_effect_get_param_by_name(filter->blur_effect, "direction");
	filter->blur_texture_size = gs_effect_get_param_by_name(filter->blur_effect, "texture_size");
	filter->blur_pixel_size = gs_effect_get_param_by_name(filter->blur_effect, "pixel_size");
	filter->composite_image = gs_effect_get_param_by_name(filter->composite_effect, "image");
	filter->composite_original = gs_effect_get_param_by_name(filter->composite_effect, "original_image");
	filter->composite_mix = gs_effect_get_param_by_name(filter->composite_effect, "mix_amount");
	if (!filter->blur_image || !filter->blur_direction || !filter->blur_texture_size ||
	    !filter->blur_pixel_size || !filter->composite_image || !filter->composite_original ||
	    !filter->composite_mix) {
		blog(LOG_ERROR, "[BlurGo] Required shader parameters are missing; the filter was not created");
		blurgo_filter_destroy(filter);
		return NULL;
	}

	blurgo_filter_update(filter, settings);
	return filter;
}

static void blurgo_filter_defaults(obs_data_t *settings)
{
	struct blurgo_settings defaults;
	blurgo_settings_defaults(&defaults);

	obs_data_set_default_int(settings, SETTING_MODE, defaults.mode);
	obs_data_set_default_double(settings, SETTING_RADIUS, defaults.radius);
	obs_data_set_default_int(settings, SETTING_PASSES, defaults.passes);
	obs_data_set_default_double(settings, SETTING_PIXEL_SIZE, defaults.pixel_size);
	obs_data_set_default_double(settings, SETTING_MIX, defaults.mix * 100.0f);
}

static void update_property_visibility(obs_properties_t *properties, enum blurgo_mode mode)
{
	const bool is_blur = mode == BLURGO_MODE_GAUSSIAN || mode == BLURGO_MODE_BOX;
	obs_property_set_visible(obs_properties_get(properties, SETTING_RADIUS), is_blur);
	obs_property_set_visible(obs_properties_get(properties, SETTING_PASSES), is_blur);
	obs_property_set_visible(obs_properties_get(properties, SETTING_PIXEL_SIZE), mode == BLURGO_MODE_PIXELATE);
}

static bool mode_modified(obs_properties_t *properties, obs_property_t *property, obs_data_t *settings)
{
	UNUSED_PARAMETER(property);
	update_property_visibility(properties, (enum blurgo_mode)obs_data_get_int(settings, SETTING_MODE));
	return true;
}

static obs_properties_t *blurgo_filter_properties(void *data)
{
	struct blurgo_filter_data *filter = data;
	obs_properties_t *properties = obs_properties_create();

	obs_properties_add_text(properties, "usage_hint", obs_module_text("BlurGo.UsageHint"), OBS_TEXT_INFO);

	obs_property_t *mode = obs_properties_add_list(properties, SETTING_MODE, obs_module_text("BlurGo.Mode"),
						     OBS_COMBO_TYPE_LIST, OBS_COMBO_FORMAT_INT);
	obs_property_list_add_int(mode, obs_module_text("BlurGo.Mode.Gaussian"), BLURGO_MODE_GAUSSIAN);
	obs_property_list_add_int(mode, obs_module_text("BlurGo.Mode.Box"), BLURGO_MODE_BOX);
	obs_property_list_add_int(mode, obs_module_text("BlurGo.Mode.Pixelate"), BLURGO_MODE_PIXELATE);
	obs_property_set_modified_callback(mode, mode_modified);

	obs_property_t *radius = obs_properties_add_float_slider(properties, SETTING_RADIUS,
							       obs_module_text("BlurGo.Radius"), 0.0, 64.0, 0.5);
	obs_property_set_long_description(radius, obs_module_text("BlurGo.Radius.Description"));

	obs_property_t *passes = obs_properties_add_int_slider(properties, SETTING_PASSES,
							    obs_module_text("BlurGo.Passes"), 1, 4, 1);
	obs_property_set_long_description(passes, obs_module_text("BlurGo.Passes.Description"));

	obs_property_t *pixel_size = obs_properties_add_float_slider(properties, SETTING_PIXEL_SIZE,
								   obs_module_text("BlurGo.PixelSize"), 2.0, 256.0, 1.0);
	obs_property_set_long_description(pixel_size, obs_module_text("BlurGo.PixelSize.Description"));

	obs_properties_add_float_slider(properties, SETTING_MIX, obs_module_text("BlurGo.Mix"), 0.0, 100.0, 1.0);

	update_property_visibility(properties, filter ? filter->settings.mode : BLURGO_MODE_GAUSSIAN);
	return properties;
}

static void ensure_render_format(gs_texrender_t **render, enum gs_color_format format)
{
	if (*render && gs_texrender_get_format(*render) == format)
		return;

	gs_texrender_destroy(*render);
	*render = gs_texrender_create(format, GS_ZS_NONE);
}

static bool capture_target(struct blurgo_filter_data *filter, obs_source_t *target, obs_source_t *parent,
			   uint32_t width, uint32_t height, enum gs_color_space space)
{
	gs_texrender_reset(filter->input);
	gs_blend_state_push();
	gs_blend_function(GS_BLEND_ONE, GS_BLEND_ZERO);

	bool captured = gs_texrender_begin_with_color_space(filter->input, width, height, space);
	if (captured) {
		struct vec4 clear_color;
		vec4_zero(&clear_color);
		gs_clear(GS_CLEAR_COLOR, &clear_color, 0.0f, 0);
		gs_ortho(0.0f, (float)width, 0.0f, (float)height, -100.0f, 100.0f);

		const uint32_t flags = obs_source_get_output_flags(target);
		const bool custom_draw = (flags & OBS_SOURCE_CUSTOM_DRAW) != 0;
		const bool asynchronous = (flags & OBS_SOURCE_ASYNC) != 0;
		if (target == parent && !custom_draw && !asynchronous)
			obs_source_default_render(target);
		else
			obs_source_video_render(target);

		gs_texrender_end(filter->input);
	}

	gs_blend_state_pop();
	return captured;
}

static bool render_pass(struct blurgo_filter_data *filter, gs_texrender_t *destination, gs_texture_t *source,
			const char *technique, const struct vec2 *direction, const struct vec2 *texture_size,
			uint32_t width, uint32_t height, enum gs_color_space space)
{
	gs_texrender_reset(destination);
	gs_blend_state_push();
	gs_blend_function(GS_BLEND_ONE, GS_BLEND_ZERO);

	bool rendered = gs_texrender_begin_with_color_space(destination, width, height, space);
	if (rendered) {
		struct vec4 clear_color;
		vec4_zero(&clear_color);
		gs_clear(GS_CLEAR_COLOR, &clear_color, 0.0f, 0);
		gs_ortho(0.0f, (float)width, 0.0f, (float)height, -100.0f, 100.0f);

		gs_effect_set_texture(filter->blur_image, source);
		gs_effect_set_vec2(filter->blur_direction, direction);
		gs_effect_set_vec2(filter->blur_texture_size, texture_size);
		gs_effect_set_float(filter->blur_pixel_size, filter->settings.pixel_size);
		while (gs_effect_loop(filter->blur_effect, technique))
			gs_draw_sprite(source, 0, width, height);

		gs_texrender_end(destination);
	}

	gs_blend_state_pop();
	return rendered;
}

static gs_texture_t *process_blur(struct blurgo_filter_data *filter, gs_texture_t *source, uint32_t width,
				  uint32_t height, enum gs_color_space space)
{
	struct vec2 texture_size;
	vec2_set(&texture_size, (float)width, (float)height);

	if (filter->settings.mode == BLURGO_MODE_PIXELATE) {
		struct vec2 unused_direction;
		vec2_zero(&unused_direction);
		if (!render_pass(filter, filter->ping, source, "Pixelate", &unused_direction, &texture_size, width,
				 height, space))
			return NULL;
		return gs_texrender_get_texture(filter->ping);
	}

	gs_texture_t *current = source;
	const float step = filter->settings.radius / 3.0f;
	const char *technique = blurgo_mode_technique(filter->settings.mode);

	for (int pass = 0; pass < filter->settings.passes; pass++) {
		struct vec2 horizontal;
		struct vec2 vertical;
		vec2_set(&horizontal, step / (float)width, 0.0f);
		vec2_set(&vertical, 0.0f, step / (float)height);

		if (!render_pass(filter, filter->ping, current, technique, &horizontal, &texture_size, width, height,
				 space))
			return NULL;
		current = gs_texrender_get_texture(filter->ping);

		if (!render_pass(filter, filter->pong, current, technique, &vertical, &texture_size, width, height,
				 space))
			return NULL;
		current = gs_texrender_get_texture(filter->pong);
	}

	return current;
}

static void draw_composite(struct blurgo_filter_data *filter, gs_texture_t *processed, gs_texture_t *original,
			   uint32_t width, uint32_t height)
{
	gs_effect_set_texture(filter->composite_image, processed);
	gs_effect_set_texture(filter->composite_original, original);
	gs_effect_set_float(filter->composite_mix, filter->settings.mix);

	gs_blend_state_push();
	gs_blend_function(GS_BLEND_ONE, GS_BLEND_INVSRCALPHA);
	while (gs_effect_loop(filter->composite_effect, "Draw"))
		gs_draw_sprite(processed, 0, width, height);
	gs_blend_state_pop();
}

static void blurgo_filter_render(void *data, gs_effect_t *effect)
{
	struct blurgo_filter_data *filter = data;
	obs_source_t *target = obs_filter_get_target(filter->context);
	obs_source_t *parent = obs_filter_get_parent(filter->context);

	if (!target || !parent) {
		obs_source_skip_video_filter(filter->context);
		return;
	}
	if (!blurgo_settings_has_visible_effect(&filter->settings)) {
		obs_source_skip_video_filter(filter->context);
		return;
	}

	const uint32_t width = obs_source_get_base_width(target);
	const uint32_t height = obs_source_get_base_height(target);
	if (!width || !height) {
		obs_source_skip_video_filter(filter->context);
		return;
	}

	const enum gs_color_space preferred_spaces[] = {GS_CS_SRGB, GS_CS_SRGB_16F, GS_CS_709_EXTENDED};
	const enum gs_color_space space =
		obs_source_get_color_space(target, OBS_COUNTOF(preferred_spaces), preferred_spaces);
	const enum gs_color_format format = gs_get_format_from_space(space);
	ensure_render_format(&filter->input, format);
	ensure_render_format(&filter->ping, format);
	ensure_render_format(&filter->pong, format);

	if (!filter->input || !filter->ping || !filter->pong ||
	    !capture_target(filter, target, parent, width, height, space)) {
		obs_source_skip_video_filter(filter->context);
		return;
	}

	gs_texture_t *original = gs_texrender_get_texture(filter->input);
	gs_texture_t *processed = process_blur(filter, original, width, height, space);
	if (!processed) {
		obs_source_skip_video_filter(filter->context);
		return;
	}

	draw_composite(filter, processed, original, width, height);
	UNUSED_PARAMETER(effect);
}

static enum gs_color_space blurgo_filter_get_color_space(void *data, size_t count,
						  const enum gs_color_space *preferred_spaces)
{
	struct blurgo_filter_data *filter = data;
	obs_source_t *target = obs_filter_get_target(filter->context);
	if (!target)
		return count ? preferred_spaces[0] : GS_CS_SRGB;
	return obs_source_get_color_space(target, count, preferred_spaces);
}

struct obs_source_info blurgo_filter = {
	.id = "blurgo_filter",
	.type = OBS_SOURCE_TYPE_FILTER,
	.output_flags = OBS_SOURCE_VIDEO,
	.get_name = blurgo_filter_get_name,
	.create = blurgo_filter_create,
	.destroy = blurgo_filter_destroy,
	.update = blurgo_filter_update,
	.get_defaults = blurgo_filter_defaults,
	.get_properties = blurgo_filter_properties,
	.video_render = blurgo_filter_render,
	.video_get_color_space = blurgo_filter_get_color_space,
};
