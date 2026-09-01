#include "blurgo-settings.h"

#include <assert.h>
#include <string.h>

static void defaults_are_stable(void)
{
	struct blurgo_settings settings;
	blurgo_settings_defaults(&settings);

	assert(settings.mode == BLURGO_MODE_GAUSSIAN);
	assert(settings.radius == 12.0f);
	assert(settings.passes == 2);
	assert(settings.pixel_size == 16.0f);
	assert(settings.mix == 1.0f);
}

static void invalid_values_are_normalized(void)
{
	struct blurgo_settings settings = {
		.mode = (enum blurgo_mode)99,
		.radius = -10.0f,
		.passes = 12,
		.pixel_size = 900.0f,
		.mix = 3.0f,
	};

	blurgo_settings_normalize(&settings);

	assert(settings.mode == BLURGO_MODE_GAUSSIAN);
	assert(settings.radius == 0.0f);
	assert(settings.passes == 4);
	assert(settings.pixel_size == 256.0f);
	assert(settings.mix == 1.0f);
}

static void techniques_match_modes(void)
{
	assert(strcmp(blurgo_mode_technique(BLURGO_MODE_GAUSSIAN), "Gaussian") == 0);
	assert(strcmp(blurgo_mode_technique(BLURGO_MODE_BOX), "Box") == 0);
	assert(strcmp(blurgo_mode_technique(BLURGO_MODE_PIXELATE), "Pixelate") == 0);
}

int main(void)
{
	defaults_are_stable();
	invalid_values_are_normalized();
	techniques_match_modes();
	return 0;
}
