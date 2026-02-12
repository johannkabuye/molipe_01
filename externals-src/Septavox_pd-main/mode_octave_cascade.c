/*
 * mode_octave_cascade.c
 *
 *  Created on: Jan 6, 2015
 *      Author: owen
 */

#include "pp6.h"
#include "oscillator.h"
#include "line.h"
#include "sad.h"
#include "audio.h"
#include "wave_synth.h"
#include "mode_octave_cascade.h"

void mode_octave_cascade_init(pocket_piano *pp6){
	uint8_t i;
	for (i = 0; i<4; i++){
		bl_saw_reset(&(pp6->mode_octave_cascade_saws[i]));
		sad_init(&(pp6->mode_octave_cascade_amp_env[i]));
		bl_square_init(&(pp6->mode_octave_cascade_squares[i]));
        pp6->mode_octave_cascade_octave_shift[i] = 0;
	}

    pp6->mode_octave_cascade_click = 0;
    pp6->mode_octave_cascade_click_count = 0;
    pp6->mode_octave_cascade_l = 0;
    pp6->mode_octave_cascade_midi_clk_last = 0;
}

float mode_octave_cascade_sample_process (pocket_piano *pp6) {
	uint8_t i;
    uint8_t midi_clk = pp6_get_midi_clock_count(pp6);

    if (pp6_midi_clock_present(pp6)){
        if (midi_clk != pp6->mode_octave_cascade_midi_clk_last){

            if (pp6_get_knob_3(pp6) < .25f) {
                if (!(pp6_get_midi_clock_count(pp6) % 3)) {
                    pp6->mode_octave_cascade_click = 1;
                }
            }
            else if (pp6_get_knob_3(pp6) < .5f) {
                if (!(pp6_get_midi_clock_count(pp6) % 6)) {
                    pp6->mode_octave_cascade_click = 1;
                }
            }
            else if (pp6_get_knob_3(pp6) < .75f) {
                if (!(pp6_get_midi_clock_count(pp6) % 8)) {
                    pp6->mode_octave_cascade_click = 1;
                }
            }
            else if (pp6_get_knob_3(pp6) < 1.1f) {
                if (!(pp6_get_midi_clock_count(pp6) % 12)) {
                    pp6->mode_octave_cascade_click = 1;
                }
            }
            pp6->mode_octave_cascade_midi_clk_last = midi_clk;
        }  // a new tick recieved
    } // midi clock present
    else {
        pp6->mode_octave_cascade_click_count++;
        if (pp6->mode_octave_cascade_click_count > ((10000 * (1 - pp6_get_knob_3(pp6))) + 4) ) {
            pp6->mode_octave_cascade_click_count = 0;
            pp6->mode_octave_cascade_click = 1;
        }
    }

    if (pp6->mode_octave_cascade_click) {
        pp6->mode_octave_cascade_click = 0;
        pp6->mode_octave_cascade_l++;
        pp6->mode_octave_cascade_l &= 3;
        // find octave shifts for each voice
        pp6->mode_octave_cascade_count2++;
        if (pp6->mode_octave_cascade_count2 > 2) pp6->mode_octave_cascade_count2 = 0;

        // do strage octave shifting  sounds cool,
        // don't know how it works exactly, you'll have to ask chris
        if (pp6->mode_octave_cascade_count2 ==0) {
            for (i = 0; i < 4; i++){
                pp6->mode_octave_cascade_octave_shift[i] = ((pp6->mode_octave_cascade_l+i) & 3);
            }
        }
        else if (pp6->mode_octave_cascade_count2 == 1) {
            for (i = 0; i < 4; i++){
                pp6->mode_octave_cascade_octave_shift[i] =  ((pp6->mode_octave_cascade_l + ((i & 1) * 2)) & 3);
            }
        }
        else if (pp6->mode_octave_cascade_count2 == 2) {
            for (i = 0; i < 4; i++){
                pp6->mode_octave_cascade_octave_shift[i] = pp6->mode_octave_cascade_l;
            }
        }

        // update synth
        for (i=0; i<4; i++){
            if (pp6->voices[i]) {
                pp6->freqs[i] = c_to_f(pp6->voices[i] * 100) * 2 / (1 << pp6->mode_octave_cascade_octave_shift[i]);
                sad_set(&(pp6->mode_octave_cascade_amp_env[i]), .01f, (pp6_get_knob_2(pp6) * 2.f) + .01f);
                sad_go(&(pp6->mode_octave_cascade_amp_env[i]));
            }
            else {
                pp6->freqs[i] = 0.1f;
            }
        }
    }

	// dsp
	for (i = 0; i < 4; i++) {
		pp6->amps[i] = sad_process(&(pp6->mode_octave_cascade_amp_env[i]));
		pp6->amps[i] = pp6->amps[i] * pp6->amps[i];   
	}

	return wave_synth_process(pp6);
}
