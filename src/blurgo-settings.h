/*
BlurGo for OBS
Copyright (C) 2026 BlurGo contributors

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
*/

#pragma once

#include <stdbool.h>

enum blurgo_mode {
	BLURGO_MODE_GAUSSIAN = 0,
	BLURGO_MODE_BOX = 1,
	BLURGO_MODE_PIXELATE = 2,
};

struct blurgo_settings {
	enum blurgo_mode mode;
	float radius;
	int passes;
	float pixel_size;
	float mix;
};

void blurgo_settings_defaults(struct blurgo_settings *settings);
void blurgo_settings_normalize(struct blurgo_settings *settings);
bool blurgo_settings_has_visible_effect(const struct blurgo_settings *settings);
const char *blurgo_mode_technique(enum blurgo_mode mode);
