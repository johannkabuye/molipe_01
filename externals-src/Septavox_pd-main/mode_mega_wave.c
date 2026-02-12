/*
 * mode_mega_wave.c
 *
 *  Created on: Jan 8, 2015
 *      Author: owen
 */

#include "oscillator.h"
#include "pp6.h"
#include "audio.h"
#include "mode_mega_wave.h"
#include "line.h"

void mode_mega_wave_init(pocket_piano *pp6){
	uint8_t i, j;
	for (i = 0; i < 4; i++){
		for (j = 0; j< 4; j++){
			pp6->mode_mega_wave_waves[i][j].phase_accum = 0;
			sin_set(&(pp6->mode_mega_wave_waves[i][j]), pp6->mode_mega_wave_freqs[i][j], 1.f);
		}
		line_set(&(pp6->mode_mega_wave_framps[i]), 100.f);
	}
}

float mode_mega_wave_sample_process (pocket_piano *pp6) {
	uint8_t i, j;
	float sigs[4];
	float cents;
	float knob1;
    
    // ctrl
	for (i=0;i<4;i++){
		if (pp6->voices[i] != pp6->mode_mega_wave_voices_last[i]){
			if (pp6->voices[i]) {
				cents = (pp6->voices[i] * 100) + 1200;
				line_go(&(pp6->mode_mega_wave_framps[i]), cents, (pp6_get_knob_3(pp6) + .001f) * 1500.f);
				line_go(&(pp6->mode_mega_wave_aramps[i]), 1, 5);
			}
			else {
                pp6->mode_mega_wave_freqs[i][0] = 0.1f;
				pp6->mode_mega_wave_freqs[i][1] = 0.1f;
				pp6->mode_mega_wave_freqs[i][2] = 0.1f;
				pp6->mode_mega_wave_freqs[i][3] = 0.1f;
				line_go(&(pp6->mode_mega_wave_aramps[i]), 0, 500);
			}
			pp6->mode_mega_wave_voices_last[i] = pp6->voices[i];
		}
	}

    // dsp
	for (i = 0; i < 4; i++){
		sigs[i] = 0;
		pp6->mode_mega_wave_freqs[i][0] = c_to_f(line_process(&(pp6->mode_mega_wave_framps[i])));
		pp6->mode_mega_wave_freqs[i][1] = pp6->mode_mega_wave_freqs[i][0] + (pp6_get_knob_2(pp6) * 10.f);
		pp6->mode_mega_wave_freqs[i][2] = pp6->mode_mega_wave_freqs[i][0] + (pp6_get_knob_2(pp6) * 20.f);
		pp6->mode_mega_wave_freqs[i][3] = pp6->mode_mega_wave_freqs[i][0] + (pp6_get_knob_2(pp6) * 30.f);
	}

	if (pp6->aux_button_count == 0) pp6->wavetable_selector = 0;
	if (pp6->aux_button_count == 1) pp6->wavetable_selector = 1;
	if (pp6->aux_button_count == 2) pp6->wavetable_selector = 2;
	if (pp6->aux_button_count == 3) pp6->wavetable_selector = 3;
	if (pp6->aux_button_count == 4) pp6->wavetable_selector = 4;
	if (pp6->aux_button_count == 5) pp6->wavetable_selector = 5;
	if (pp6->aux_button_count == 6) pp6->wavetable_selector = 6;

	knob1 = pp6_get_knob_1(pp6) + 1;
	for (i = 0; i < 4; i++){
		for (j = 0; j< 4; j++){
			sin_set(&(pp6->mode_mega_wave_waves[i][j]), pp6->mode_mega_wave_freqs[i][j] * knob1, 1.f);
			sigs[i] += sin_process_simple(&(pp6->mode_mega_wave_waves[i][j]), pp6->wavetable_selector) * .05f;
		}
		sigs[i] *= line_process(&(pp6->mode_mega_wave_aramps[i]));;
	}

	return sigs[0] + sigs[1] + sigs[2] + sigs[3];
}


