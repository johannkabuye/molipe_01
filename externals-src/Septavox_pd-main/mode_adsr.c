/*
 * mode_adsr.c
 *
 *  Created on: Dec 11, 2014
 *      Author: owen
 */

#include "oscillator.h"
#include "pp6.h"
#include "audio.h"
#include "sadsr.h"
#include "wave_synth.h"
#include "mode_adsr.h"

void mode_adsr_init(pocket_piano *pp6){
	uint8_t i;
	for (i = 0; i<4; i++){
		sadsr_init(&(pp6->mode_adsr_amp_env[i]));
	}
}

float mode_adsr_sample_process (pocket_piano *pp6) {

	uint8_t i;

	for (i=0;i<4;i++){
		sadsr_set(&(pp6->mode_adsr_amp_env[i]), pp6_get_knob_3(pp6) * 1.f, pp6_get_knob_2(pp6) * 1.f, pp6_get_knob_2(pp6) * 2.f, .8f);
	}

	for (i=0;i<4;i++){
		if (pp6->voices[i] != pp6->voices_last[i]){
			if (pp6->voices[i])
				pp6->freqs[i] = c_to_f(pp6->voices[i] * 100) * 2;

			if (pp6->voices[i] ) {
				sadsr_go(&(pp6->mode_adsr_amp_env[i]));
			}
			else {
				sadsr_release(&(pp6->mode_adsr_amp_env[i]));
			}
			pp6->voices_last[i] = pp6->voices[i];
		}
	}

    // dsp
	for (i = 0; i < 4; i++) {
		pp6->amps[i] = sadsr_process(&(pp6->mode_adsr_amp_env[i]));
		pp6->amps[i] = pp6->amps[i] * pp6->amps[i]; 
	}

	return wave_synth_process(pp6);

}
