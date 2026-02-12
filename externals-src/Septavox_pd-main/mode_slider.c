/*
 * mode_slider.c
 *
 *  Created on: Jan 7, 2015
 *      Author: owen
 */

#include "oscillator.h"
#include "pp6.h"
#include "audio.h"
#include "mode_slider.h"
#include "wave_synth.h"
#include "sadsr.h"
#include "line.h"

void mode_slider_init(pocket_piano *pp6){
	uint8_t i;
	for (i = 0; i<4; i++){
		sadsr_init(&(pp6->mode_slider_amp_env[i]));
	    pp6->mode_slider_note_dur[i] = 0;
        pp6->mode_slider_voices_last[i] = 0;
    }
}

void mode_slider_stop_notes(pocket_piano *pp6){
	uint8_t i;
	for (i = 0; i<4; i++){
		pp6->mode_slider_note_dur[i] = 0;
		sadsr_init(&(pp6->mode_slider_amp_env[i]));
	}
}

float mode_slider_sample_process (pocket_piano *pp6) {
	uint8_t i;
	float cents;
	float quickly;

	for (i=0;i<4;i++){
		if (pp6->voices[i] != pp6->mode_slider_voices_last[i]){
	        quickly = pp6_get_knob_3(pp6) *  pp6_get_knob_3(pp6);
			if (pp6->voices[i] ) {
				/////
				pp6->mode_slider_note_dur[i] = 0;
				sadsr_set(&(pp6->mode_slider_amp_env[i]), .01f, .2f, .15f, .85f);
				cents = (pp6->voices[i] * 100) + 1200;
				line_set(&(pp6->mode_slider_framps[i]), cents + ((pp6_get_knob_2(pp6) - .5f)  * 2400.f));   // 2400 cents sharp
				line_go(&(pp6->mode_slider_framps[i]), cents, (quickly + .001f) * 1500.f);
				sadsr_go(&(pp6->mode_slider_amp_env[i]));
			}
			else {
				sadsr_set(&(pp6->mode_slider_amp_env[i]), .01f, .1f, (pp6->mode_slider_note_dur[i] * 128) / SR, .85f);
				sadsr_release(&(pp6->mode_slider_amp_env[i]));
			}
			pp6->mode_slider_voices_last[i] = pp6->voices[i];
		}
		pp6->mode_slider_note_dur[i]++;
	}


	for (i = 0; i < 4; i++) {
		pp6->amps[i] = sadsr_process(&(pp6->mode_slider_amp_env[i]));
		pp6->amps[i] = pp6->amps[i] * pp6->amps[i]; 
		pp6->freqs[i] = c_to_f(line_process(&(pp6->mode_slider_framps[i])));;
	}

	return wave_synth_process(pp6);
}

