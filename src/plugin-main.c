/*
BlurGo for OBS
Copyright (C) 2026 BlurGo contributors

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <https://www.gnu.org/licenses/>
*/

#include <obs-module.h>
#include <plugin-support.h>

OBS_DECLARE_MODULE()
OBS_MODULE_USE_DEFAULT_LOCALE(PLUGIN_NAME, "en-US")

extern struct obs_source_info blurgo_filter;

MODULE_EXPORT const char *obs_module_description(void)
{
	return "Production-grade GPU blur filters for OBS Studio sources and scenes";
}

MODULE_EXPORT const char *obs_module_author(void)
{
	return "BlurGo contributors";
}

bool obs_module_load(void)
{
	obs_register_source(&blurgo_filter);
	obs_log(LOG_INFO, "loaded successfully (version %s)", PLUGIN_VERSION);
	return true;
}

void obs_module_unload(void)
{
	obs_log(LOG_INFO, "plugin unloaded");
}
