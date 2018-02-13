/*
 * This file is part of mpv.
 *
 * mpv is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * mpv is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with mpv.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libavutil/common.h>

#include "mpv_talloc.h"

#include "ao.h"
#include "ao_cb.h"
#include "audio/format.h"
#include "common/msg.h"
#include "internal.h"
#include "options/m_option.h"
#include "osdep/timer.h"

static struct ao *ao_cb = NULL;

int audio_callback(uint16_t *stream, int len)
{
    struct ao *ao = ao_cb;

    if (ao == NULL) {
		MP_ERR(ao, "audio callback was not initialised");
		return -1;
	}

	if (stream == NULL) {
		MP_ERR(ao, "stream must not be NULL");
		return -2;
	}

    if (len % ao->sstride)
        MP_ERR(ao, "audio callback not sample aligned");

    /* Time this buffer will take, plus assume 1 period (1 callback invocation)
     * fixed latency.
     */
    double delay = 2 * len / (double)ao->bps;
    void *data[1] = {stream};
	struct ao_convert_fmt conv = {
		.src_fmt    = AF_FORMAT_S16,
		.channels   = 2,
		.dst_bits   = 16,
		.pad_lsb    = 0,
	};

	return ao_read_data_converted(ao, &conv, data, len / ao->sstride,
			mp_time_us() + 1000000LL * delay);
}

static int init(struct ao *ao)
{
	ao->format = AF_FORMAT_S16;
	mp_chmap_from_channels(&ao->channels, 2);
    ao->bps = ao->channels.num * ao->samplerate * af_fmt_to_bytes(ao->format);

	MP_INFO(ao, "Samplerate: %d Hz Channels: %d Format: %s\n", ao->samplerate,
			ao->channels.num, af_fmt_to_str(ao->format));

	/* Setup for audio callback */
	ao_cb = ao;

    return 0;
}

static void uninit(struct ao *ao)
{
	ao_cb = NULL;
	return;
}

static void resume (struct ao *ao)
{
	return;
}

#define OPT_BASE_STRUCT struct priv

const struct ao_driver audio_out_audio_cb = {
    .description = "Audio callback for libmpv",
    .name      = "audio-cb",
    .init      = init,
	.uninit    = uninit,
	.resume    = resume,
    .priv_size = 0,
    .priv_defaults = NULL,
    .options = NULL,
    .options_prefix = NULL,
};
