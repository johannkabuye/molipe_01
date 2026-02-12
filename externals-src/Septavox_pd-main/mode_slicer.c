/*
 * mode_slicer.c
 *
 *  Created on: Jan 6, 2015
 *      Author: owen
 */


#include "oscillator.h"
#include "pp6.h"
#include "audio.h"
#include "mode_slicer.h"
#include "wave_synth.h"
#include "line.h"

static uint8_t pattern[9][24] = {
		{0,0,0,0, 0,0,0,0, 0,0,0,0, 1,1,1,1, 1,1,1,1, 1,1,1,1},
		{0,0,0,0, 1,1,1,1, 0,0,0,1, 1,1,1,0, 0,1,1,0, 1,0,1,0},
		{0,0,0,0, 1,1,1,1, 0,0,0,0, 1,1,1,1, 1,1,1,1, 1,1,1,1},
		{1,1,1,0, 0,0,0,1, 1,0,0,0, 1,1,1,1, 0,0,0,0, 1,1,0,0}, //swing


		{0,0,1,1, 1,1,1,1, 0,0,0,0, 0,0,1,1, 0,0,1,1, 1,0,0,0},
		{1,1,1,1, 0,0,0,0, 0,0,0,0, 1,1,1,1, 0,0,0,0, 1,1,0,0},
		{0,0,0,0, 0,0,0,0, 1,0,1,0, 1,1,0,0, 1,1,1,1, 1,1,1,1}, //end of song articulation
		{0,0,0,1, 0,0,1,0, 0,1,0,0, 1,0,0,0, 0,0,1,1, 0,1,1,0}, //morse
		{0,0,0,0, 0,0,0,0, 0,0,0,1, 0,0,0,0, 0,0,0,0, 0,0,0,1,}
};

void mode_slicer_init(pocket_piano *pp6){
	uint8_t i;

    line_set(&(pp6->mode_slicer_slice_line), 0);

    pp6->mode_slicer_step = 0;
    pp6->mode_slicer_sample_counter = 0;
    pp6->mode_slicer_slice_amp = 0;
    pp6->mode_slicer_slice_amp_last = 0;
	
    for (i = 0; i<4; i++){
        pp6->mode_slicer_voices_last[i] = 0;
        pp6->mode_slicer_amps[i] = 0;
    }
}

float mode_slicer_sample_process (pocket_piano *pp6) {
	uint8_t i;

	for (i=0;i<4;i++){
		if (pp6->voices[i] != pp6->mode_slicer_voices_last[i]){
			if (pp6->voices[i]) {
				pp6->mode_slicer_freqs[i] = c_to_f(pp6->voices[i] * 100) * 2;
				line_go(&(pp6->mode_slicer_aramps[i]), 1, 5);

			}
			else {
				pp6->mode_slicer_freqs[i] = 0.1f;
				line_go(&(pp6->mode_slicer_aramps[i]), 0, 20);
			}
			pp6->mode_slicer_voices_last[i] = pp6->voices[i];
		}
	}

	//click along ,  do it from midi clock , or manual
	if (pp6_midi_clock_present(pp6)){
		pp6->mode_slicer_step = pp6_get_midi_clock_count(pp6);
	}
	else {
		pp6->mode_slicer_sample_counter++;

		if (pp6->mode_slicer_sample_counter > ((1 - pp6_get_knob_3(pp6)) * 5000.f)){
			pp6->mode_slicer_sample_counter = 0;
			pp6->mode_slicer_step++;
			if (pp6->mode_slicer_step == 24) pp6->mode_slicer_step = 0;
		}
	}

	for (i = 0; i < 4; i++) {
		pp6->freqs[i] = pp6->mode_slicer_freqs[i];
		pp6->amps[i] = line_process(&(pp6->mode_slicer_aramps[i]));
	}

	pp6->mode_slicer_slice_amp = (float)pattern[(uint8_t)(pp6_get_knob_2(pp6) * 9)][pp6->mode_slicer_step];

	if (pp6->mode_slicer_slice_amp != pp6->mode_slicer_slice_amp_last){
		line_go(&(pp6->mode_slicer_slice_line), (float)pp6->mode_slicer_slice_amp, 3.f);
		pp6->mode_slicer_slice_amp_last = pp6->mode_slicer_slice_amp;
	}
	pp6->mode_slicer_sliced = line_process(&(pp6->mode_slicer_slice_line));

	return wave_synth_process(pp6) * pp6->mode_slicer_sliced;
}


