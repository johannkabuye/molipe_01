/*
 * eq.c
 *
 *  Created on: Aug 21, 2012
 *      Author: owen
 */

#include "eq.h"


// -----------
//| Constants |
// -----------

static float32_t vsa = (1.0 / 4294967295.0f); // Very small amount (Denormal Fix)


// ---------------
//| Initialise EQ |
// ---------------

// Recommended frequencies are ...
//
// lowfreq = 880 Hz
// highfreq = 5000 Hz
//
// Set mixfreq to whatever rate your system is using (eg 48Khz)

void init_3band_state(EQSTATE* es, int32_t lowfreq, int32_t highfreq, int32_t mixfreq)
{
	// Clear state

	memset(es,0,sizeof(EQSTATE));

	// Set Low/Mid/High gains to unity

	es->lg = 2.5;   //  150 % bass boost
	es->mg = 1.0;
	es->hg = 1.0;

	// Calculate filter cutoff frequencies

	es->lf = 2 * sinf(PI * ((float32_t)lowfreq / (float32_t)mixfreq));
	es->hf = 2 * sinf(PI * ((float32_t)highfreq / (float32_t)mixfreq));
}


// ---------------
//| EQ one sample |
// ---------------

// - sample can be any range you like :)
//
// Note that the output will depend on the gain settings for each band
// (especially the bass) so may require clipping before output, but you
// knew that anyway :)

float32_t do_3band(EQSTATE* es, float32_t sample)
{

	float32_t l,m,h; // Low / Mid / High - Sample Values

	// Filter #1 (lowpass)

	es->f1p0 += (es->lf * (sample - es->f1p0)) + vsa;
	es->f1p1 += (es->lf * (es->f1p0 - es->f1p1));
	es->f1p2 += (es->lf * (es->f1p1 - es->f1p2));
	es->f1p3 += (es->lf * (es->f1p2 - es->f1p3));

	l = es->f1p3;

	// Filter #2 (highpass)

	es->f2p0 += (es->hf * (sample - es->f2p0)) + vsa;
	es->f2p1 += (es->hf * (es->f2p0 - es->f2p1));
	es->f2p2 += (es->hf * (es->f2p1 - es->f2p2));
	es->f2p3 += (es->hf * (es->f2p2 - es->f2p3));

	h = es->sdm3 - es->f2p3;

	// Calculate midrange (signal - (low + high))

	m = es->sdm3 - (h + l);

	// Scale, Combine and store

	l *= es->lg;
	m *= es->mg;
	h *= es->hg;

	// Shuffle history buffer

	es->sdm3 = es->sdm2;
	es->sdm2 = es->sdm1;
	es->sdm1 = sample;

	// Return result

	return(l + m + h);
}
