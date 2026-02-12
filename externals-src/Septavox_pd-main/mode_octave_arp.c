/*
 * mode_octave_arp.c
 *
 *  Created on: Oct 18, 2012
 *      Author: owen
 */

#include "oscillator.h"
#include "pp6.h"
#include "line.h"
#include "sad.h"
#include "audio.h"
#include "wave_synth.h"
#include "mode_octave_arp.h"

void mode_octave_arp_init(pocket_piano *pp6){
	uint8_t i;
	for (i = 0; i<4; i++){
		sad_init(&(pp6->mode_octave_arp_amp_env[i]));
		sad_set(&(pp6->mode_octave_arp_amp_env[i]), .01f, .5f);
	}

    pp6->mode_octave_arp_click = 0;
    pp6->mode_octave_arp_click_count = 0;
    pp6->mode_octave_arp_l = 0;
    pp6->mode_octave_arp_octave_shift = 0;
    pp6->mode_octave_arp_midi_clk_last = 0;

}

float mode_octave_arp_sample_process (pocket_piano *pp6) {
	uint8_t i;
    uint8_t midi_clk = pp6_get_midi_clock_count(pp6);

    if (pp6_midi_clock_present(pp6)){
        if (midi_clk != pp6->mode_octave_arp_midi_clk_last){

            if (pp6_get_knob_3(pp6) < .25f) {
                if (!(pp6_get_midi_clock_count(pp6) % 3)) {
                    pp6->mode_octave_arp_click = 1;
                }
            }
            else if (pp6_get_knob_3(pp6) < .5f) {
                if (!(pp6_get_midi_clock_count(pp6) % 6)) {
                    pp6->mode_octave_arp_click = 1;
                }
            }
            else if (pp6_get_knob_3(pp6) < .75f) {
                if (!(pp6_get_midi_clock_count(pp6) % 8)) {
                    pp6->mode_octave_arp_click = 1;
                }
            }
            else if (pp6_get_knob_3(pp6) < 1.1f) {
                if (!(pp6_get_midi_clock_count(pp6) % 12)) {
                    pp6->mode_octave_arp_click = 1;
                }
            }
            pp6->mode_octave_arp_midi_clk_last = midi_clk;
        }  // a new tick recieved
    } // midi clock present
    else {
        pp6->mode_octave_arp_click_count++;
        if (pp6->mode_octave_arp_click_count > ((10000 * (1 - pp6_get_knob_3(pp6))) + 1) ) {
            pp6->mode_octave_arp_click_count = 0;
            pp6->mode_octave_arp_click = 1;
        }
    }

    // play notes in the allocated voices array, so arp plays notes in the order they were pressed
    if (pp6->mode_octave_arp_click) {
        pp6->mode_octave_arp_click = 0;
        i = 0;
        do {
            pp6->mode_octave_arp_l++;
            pp6->mode_octave_arp_l &= 3;
            if (!pp6->mode_octave_arp_l) pp6->mode_octave_arp_octave_shift++;
            i++;
        }
        while (!pp6->voices[pp6->mode_octave_arp_l] && (i < 4));
        if (pp6->voices[pp6->mode_octave_arp_l]) {
            pp6->freqs[pp6->mode_octave_arp_l] = c_to_f(pp6->voices[pp6->mode_octave_arp_l] * 100) * 2 * ((pp6->mode_octave_arp_octave_shift & 1) + 1);
            sad_set(&(pp6->mode_octave_arp_amp_env[pp6->mode_octave_arp_l]), .01f, (pp6_get_knob_2(pp6) * 2.f) + .01f);
            sad_go(&(pp6->mode_octave_arp_amp_env[pp6->mode_octave_arp_l]));
        }
        else {
        }
    }

	// dsp process envelopes
	for (i = 0; i < 4; i++) {
		pp6->amps[i] = sad_process(&(pp6->mode_octave_arp_amp_env[i]));
		pp6->amps[i] = pp6->amps[i] * pp6->amps[i];  
	}

	return wave_synth_process(pp6);
}
