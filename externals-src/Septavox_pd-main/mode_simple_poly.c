/*
 * mode_simple_poly.c
 *
 *  Created on: Oct 18, 2013
 *      Author: owen
 */

#include <stdint.h>
#include "oscillator.h"
#include "pp6.h"
#include "audio.h"
#include "mode_simple_poly.h"
#include "wave_synth.h"
#include "line.h"

void mode_simple_poly_init(pocket_piano *pp6){
    pp6->mode_simple_poly_voices_last[0] = 0;
    pp6->mode_simple_poly_voices_last[1] = 0;
    pp6->mode_simple_poly_voices_last[2] = 0;
    pp6->mode_simple_poly_voices_last[3] = 0;
}

float mode_simple_poly_sample_process (pocket_piano *pp6) {
	uint8_t i;
	float vibrato;
	float vibrato_depth;
	
    for (i=0;i<4;i++){
		if (pp6->voices[i] != pp6->mode_simple_poly_voices_last[i]){
			if (pp6->voices[i]) {
				pp6->mode_simple_poly_freqs[i] = c_to_f(pp6->voices[i] * 100) * 2;
				line_go(&(pp6->mode_simple_poly_aramps[i]), 1, 5);
			}
			else {
				line_go(&(pp6->mode_simple_poly_aramps[i]), 0, 20);
			}
		}
		pp6->mode_simple_poly_voices_last[i] = pp6->voices[i];
	}

	sin_set(&(pp6->mode_simple_poly_sin_lfo), 50 * pp6_get_knob_3(pp6), 1.f);
	vibrato = sin_process(&(pp6->mode_simple_poly_sin_lfo), 0);

	vibrato_depth = pp6_get_knob_2(pp6) * pp6_get_knob_2(pp6) * pp6_get_knob_2(pp6);

	for (i = 0; i < 4; i++) {
		pp6->freqs[i] = pp6->mode_simple_poly_freqs[i] + (vibrato * vibrato_depth * pp6->freqs[i] * .5);  
		pp6->amps[i] = line_process(&(pp6->mode_simple_poly_aramps[i]));
	}

	return wave_synth_process(pp6);
}

