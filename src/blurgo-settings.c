/*
BlurGo for OBS
Copyright (C) 2026 BlurGo contributors

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
*/

#include "blurgo-settings.h"

#include <math.h>

static float clamp_float(float value, float minimum, float maximum)
{
	if (value < minimum)
		return minimum;
	if (value > maximum)
		return maximum;
	return value;
}

static int clamp_int(int value, int minimum, int maximum)
{
	if (value < minimum)
		return minimum;
	if (value > maximum)
		return maximum;
	return value;
}

void blurgo_settings_defaults(struct blurgo_settings *settings)
{
	settings->mode = BLURGO_MODE_GAUSSIAN;
	settings->radius = 12.0f;
	settings->passes = 2;
	settings->pixel_size = 16.0f;
	settings->mix = 1.0f;
}

void blurgo_settings_normalize(struct blurgo_settings *settings)
{
	struct blurgo_settings defaults;
	blurgo_settings_defaults(&defaults);

	if (settings->mode < BLURGO_MODE_GAUSSIAN || settings->mode > BLURGO_MODE_PIXELATE)
		settings->mode = defaults.mode;

	if (!isfinite(settings->radius))
		settings->radius = defaults.radius;
	if (!isfinite(settings->pixel_size))
		settings->pixel_size = defaults.pixel_size;
	if (!isfinite(settings->mix))
		settings->mix = defaults.mix;

	settings->radius = clamp_float(settings->radius, 0.0f, 64.0f);
	settings->passes = clamp_int(settings->passes, 1, 4);
	settings->pixel_size = clamp_float(settings->pixel_size, 2.0f, 256.0f);
	settings->mix = clamp_float(settings->mix, 0.0f, 1.0f);
}

bool blurgo_settings_has_visible_effect(const struct blurgo_settings *settings)
{
	if (settings->mix <= 0.0f)
		return false;

	if (settings->mode == BLURGO_MODE_GAUSSIAN || settings->mode == BLURGO_MODE_BOX)
		return settings->radius > 0.0f;

	return true;
}

const char *blurgo_mode_technique(enum blurgo_mode mode)
{
	switch (mode) {
	case BLURGO_MODE_BOX:
		return "Box";
	case BLURGO_MODE_PIXELATE:
		return "Pixelate";
	case BLURGO_MODE_GAUSSIAN:
	default:
		return "Gaussian";
	}
}
