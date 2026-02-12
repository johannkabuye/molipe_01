/*
 * wave_synth.c
 *
 *  Created on: Jan 1, 2015
 *      Author: owen
 */


#include <stdint.h>
#include "audio.h"
#include "pp6.h"
#include "oscillator.h"
#include "wave_synth.h"

void wave_synth_init(pocket_piano *pp6){
	uint8_t i;
	for (i = 0; i<4; i++){
		bl_saw_reset(&(pp6->wave_synth_saws[i]));
		bl_square_init(&(pp6->wave_synth_squares[i]));
	}
}

float wave_synth_process(pocket_piano *pp6){

	uint8_t i;
	float sig;

	// just make sure freqs are never 0  cause of divide by 0 issues in the saw and square implementations
	for (i = 0; i < 4; i++) {
		if (pp6->freqs[i] == 0) {
			pp6->freqs[i] = .01f;
		}
	}

	if (pp6->aux_button_count == 0){
		pp6->wavetable_selector = 1;
		sig = 0;
		for (i = 0; i < 4; i++) {
			sin_set(&(pp6->wave_synth_sins[i]), pp6->freqs[i] * (pp6_get_knob_1(pp6) + 1), .1f);
			sig += sin_process(&(pp6->wave_synth_sins[i]), pp6->wavetable_selector) * pp6->amps[i];
		}
		sig *= 1;
	}
	if (pp6->aux_button_count == 1){
		pp6->wavetable_selector = 0;
		sig = 0;
		for (i = 0; i < 4; i++) {
			sin_set(&(pp6->wave_synth_sins[i]), pp6->freqs[i] * (pp6_get_knob_1(pp6) + 1), .1f);
			sig += sin_process(&(pp6->wave_synth_sins[i]), pp6->wavetable_selector) * pp6->amps[i];
		}
		sig *= 1;
	}
	if (pp6->aux_button_count == 2){
		pp6->wavetable_selector = 2;
		sig = 0;
		for (i = 0; i < 4; i++) {
			sin_set(&(pp6->wave_synth_sins[i]), pp6->freqs[i] * (pp6_get_knob_1(pp6) + 1), .1f);
			sig += sin_process(&(pp6->wave_synth_sins[i]), pp6->wavetable_selector) * pp6->amps[i];
		}
		sig *= 1;
	}

	if (pp6->aux_button_count == 3){
		sig = 0;
		for (i = 0; i < 4; i++) {
			bl_square_set(&(pp6->wave_synth_squares[i]), pp6->freqs[i] * (pp6_get_knob_1(pp6) + 1) );
			sig += bl_square_process(&(pp6->wave_synth_squares[i])) * pp6->amps[i];
		}
		sig *= .2f;
	}
	if (pp6->aux_button_count == 4){
		sig = 0;
		for (i = 0; i < 4; i++) {
			bl_saw_set(&(pp6->wave_synth_saws[i]), pp6->freqs[i] * (pp6_get_knob_1(pp6) + 1) );
			sig += bl_saw_process(&(pp6->wave_synth_saws[i])) * pp6->amps[i];
		}
		sig *= .2f;
	}
	if (pp6->aux_button_count == 5){
		pp6->wavetable_selector = 3;
		sig = 0;
		for (i = 0; i < 4; i++) {
			sin_set(&(pp6->wave_synth_sins[i]), pp6->freqs[i] * (pp6_get_knob_1(pp6) + 1), .1f);
			sig += sin_process(&(pp6->wave_synth_sins[i]), pp6->wavetable_selector) * pp6->amps[i];
		}
		sig *= 1;
	}
	if (pp6->aux_button_count == 6){
		pp6->wavetable_selector = 4;
		sig = 0;
		for (i = 0; i < 4; i++) {
			sin_set(&(pp6->wave_synth_sins[i]), pp6->freqs[i] * (pp6_get_knob_1(pp6) + 1), .1f);
			sig += sin_process(&(pp6->wave_synth_sins[i]), pp6->wavetable_selector) * pp6->amps[i];
		}
		sig *= 1;
	}
	return sig;
}
