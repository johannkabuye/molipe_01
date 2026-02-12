/*
 * pp6.c
 *
 *  Created on: Jun 23, 2012
 *      Author: owen
 */

#include <stdint.h>
#include "pp6.h"

#define ABS(a)	   (((a) < 0) ? -(a) : (a))

/* Private macro -------------------------------------------------------------*/
/* Private variables ---------------------------------------------------------*/

/* You can monitor the converted value by adding the variable "ADC3ConvertedValue"
   to the debugger watch window */


// keypad values
//uint32_t keys = 0xFFFFFFFF;

void pp6_init(pocket_piano *pp6) {
	uint8_t i, j;
	pp6_leds_init(pp6);
	pp6_knobs_init(pp6);
	pp6_keys_init(pp6);

	AUX_LED_BLUE_OFF;AUX_LED_RED_ON;AUX_LED_GREEN_OFF;

	pp6_set_mode(pp6, 0);

	pp6->secret_mode_enabled = 0;

    pp6->knob[0] = .5f;
    pp6->knob[1] = .5f;
    pp6->knob[2] = .5f;

	pp6->knob_touched[0] = 0;
	pp6->knob_touched[1] = 0;
	pp6->knob_touched[2] = 0;
	pp6->physical_notes_on = 0;
	pp6->midi_start_flag = 0;
	pp6->midi_stop_flag = 0;

	pp6->oct_transpose = 0;

	pp6->midi_clock_period = 0;
	pp6->midi_clock_present = 0;
	pp6->midi_in_clock_last = 0;
	pp6->midi_clock_tick_count = 0;

	pp6->mode_led_flash = 0;
	pp6->aux_led_flash = 0;

	pp6->aux_button_count = 0;

	pp6->voices[0] = 0;
	pp6->voices[1] = 0;
	pp6->voices[2] = 0;
	pp6->voices[3] = 0;

	pp6->voices_last[0] = 0;
	pp6->voices_last[1] = 0;
	pp6->voices_last[2] = 0;
	pp6->voices_last[3] = 0;

	pp6->voices_note_on_flag[0] = 0;
	pp6->voices_note_on_flag[1] = 0;
	pp6->voices_note_on_flag[2] = 0;
	pp6->voices_note_on_flag[3] = 0;


	pp6->freqs[0] = 100;
	pp6->freqs[1] = 101;
	pp6->freqs[2] = 102;
	pp6->freqs[3] = 103;
    
	pp6->amps[0] = 0;
	pp6->amps[1] = 0;
	pp6->amps[2] = 0;
	pp6->amps[3] = 0;

    pp6->wavetable_selector = 0;

	// init the note on arrays
	for (i = 0; i < 128; i++) {
		pp6->note_state[i] = 0;
		pp6->note_state_last[i] = 0;
	}

	// init keys states
	for (i = 0; i< 42; i++){
		pp6->keys[i] = 0;
		for (j = 0; j<4; j++){
			pp6->keys_history[j][i] = 0;
		}
	}

	AUX_LED_RED_ON;AUX_LED_GREEN_OFF;AUX_LED_BLUE_OFF;
}

void pp6_enable_secret_mode(pocket_piano *pp6) {
	pp6->secret_mode_enabled = 1;
}


/// MIDI clock stuff
void pp6_midi_clock_tick(pocket_piano *pp6) {
/*
	pp6->midi_clock_flag = 1; // set the flag used elsewhere

	pp6->midi_clock_period = sample_clock - pp6->midi_in_clock_last;
	pp6->midi_in_clock_last = sample_clock;

	pp6->midi_clock_tick_count++;
	if (pp6->midi_clock_tick_count == 24){
		pp6->midi_clock_tick_count = 0;
		pp6_flash_mode_led(40);
	}*/
}

uint8_t pp6_get_midi_clock_count(pocket_piano *pp6) {
	return pp6->midi_clock_tick_count;
}
uint8_t pp6_get_midi_clock_tick(pocket_piano *pp6) {
	return pp6->midi_clock_flag;
}
void pp6_clear_midi_clock_tick(pocket_piano *pp6){
	pp6->midi_clock_flag = 0;
}

void pp6_check_for_midi_clock(pocket_piano *pp6) {
    // check for presence of midi clock signal
    /*if ((sample_clock - pp6->midi_in_clock_last) > MIDI_CLOCK_TIMEOUT) {
        pp6->midi_clock_present = 0;
    }
    else {
        pp6->midi_clock_present = 1;
    }*/
}

uint8_t pp6_midi_clock_present(pocket_piano *pp6) {
	return pp6->midi_clock_present;
}

uint32_t pp6_get_midi_clock_period(pocket_piano *pp6) {
	return pp6->midi_clock_period;
}

void pp6_set_global_octave_transpose(pocket_piano *pp6, uint8_t val){
	pp6->oct_transpose = val;
}

float pp6_get_knob_1(pocket_piano *pp6){
	if (pp6->oct_transpose == 1)   // oct up
		return (pp6->knob[0] * 2) + 1;

	if (pp6->oct_transpose == 2)
		return (pp6->knob[0] * .5) - .5;

	return pp6->knob[0];   // 0 for nomal operation

}
float pp6_get_knob_1_raw(pocket_piano *pp6){
	return pp6->knob[0];
}
float pp6_get_knob_2(pocket_piano *pp6){
	return pp6->knob[1];
}
float pp6_get_knob_3(pocket_piano *pp6){
	return pp6->knob[2];
}

void pp6_set_knob_1(pocket_piano *pp6, float v){
	pp6->knob[0] = v;
}
void pp6_set_knob_2(pocket_piano *pp6, float v){
	pp6->knob[1] = v;
}
void pp6_set_knob_3(pocket_piano *pp6, float v){
	pp6->knob[2] = v;
}

float * pp6_get_knob_array(pocket_piano *pp6){
	return pp6->knob;
}

void pp6_set_knob_array(pocket_piano *pp6, float * knobs){
	pp6->knob[0] = knobs[0];
	pp6->knob[1] = knobs[1];
	pp6->knob[2] = knobs[2];
}

// mode and aux buttons
void  pp6_set_mode_button_pressed(pocket_piano *pp6){
	pp6->mode_button_pressed = 1;
}
void pp6_set_mode_button_released(pocket_piano *pp6){
	pp6->mode_button_released = 1;
}
uint8_t pp6_mode_button_pressed(pocket_piano *pp6){
	return pp6->mode_button_pressed;
}
uint8_t pp6_mode_button_released(pocket_piano *pp6){
	return pp6->mode_button_released;
}

void  pp6_set_aux_button_pressed(pocket_piano *pp6){
	pp6->aux_button_pressed = 1;
	pp6->aux_button_count += 1;
	if (pp6->aux_button_count == 7) pp6->aux_button_count = 0;
	pp6_set_aux_led(pp6, pp6->aux_button_count + 1);
}
void pp6_set_aux_button_released(pocket_piano *pp6){
	pp6->aux_button_released = 1;
}
uint8_t pp6_aux_button_pressed(pocket_piano *pp6){
	return pp6->aux_button_pressed;
}
uint8_t pp6_aux_button_released(pocket_piano *pp6){
	return pp6->aux_button_released;
}

// MODE
void pp6_change_mode(pocket_piano *pp6){
	pp6->mode++;

		if (pp6->mode == 7) pp6->mode = 0;

		pp6_set_mode_led(pp6, pp6->mode + 1);
}

void pp6_set_mode(pocket_piano *pp6, uint32_t mode){
	pp6->mode = mode;
	pp6_set_mode_led(pp6, pp6->mode + 1);
}

uint32_t pp6_get_mode(pocket_piano *pp6){
	return pp6->mode;
}

// MODE LED
void pp6_set_mode_led(pocket_piano *pp6, uint8_t led) {
	pp6->mode_led = led;
	if (!pp6->mode_led_flash) {
		if (led == 0) {MODE_LED_RED_OFF;MODE_LED_GREEN_OFF;MODE_LED_BLUE_OFF;}
		if (led == 1) {MODE_LED_RED_ON;MODE_LED_GREEN_OFF;MODE_LED_BLUE_OFF;}
		if (led == 2) {MODE_LED_RED_ON;MODE_LED_GREEN_ON;MODE_LED_BLUE_OFF;}
		if (led == 3) {MODE_LED_RED_OFF;MODE_LED_GREEN_ON;MODE_LED_BLUE_OFF;}
		if (led == 4) {MODE_LED_RED_OFF;MODE_LED_GREEN_ON;MODE_LED_BLUE_ON;}
		if (led == 5) {MODE_LED_RED_OFF;MODE_LED_GREEN_OFF;MODE_LED_BLUE_ON;}
		if (led == 6) {MODE_LED_RED_ON;MODE_LED_GREEN_OFF;MODE_LED_BLUE_ON;}
		if (led == 7) {MODE_LED_RED_ON;MODE_LED_GREEN_ON;MODE_LED_BLUE_ON;}
	}
}

uint8_t pp6_get_mode_led(pocket_piano *pp6){
	return pp6->mode_led;
}


// AUX LED
void pp6_set_aux_led(pocket_piano *pp6, uint8_t led) {
	pp6->aux_led = led;
	if (!pp6->aux_led_flash) {
		if (led == 0) {AUX_LED_RED_OFF;AUX_LED_GREEN_OFF;AUX_LED_BLUE_OFF;}
		if (led == 1) {AUX_LED_RED_ON;AUX_LED_GREEN_OFF;AUX_LED_BLUE_OFF;}
		if (led == 2) {AUX_LED_RED_ON;AUX_LED_GREEN_ON;AUX_LED_BLUE_OFF;}
		if (led == 3) {AUX_LED_RED_OFF;AUX_LED_GREEN_ON;AUX_LED_BLUE_OFF;}
		if (led == 4) {AUX_LED_RED_OFF;AUX_LED_GREEN_ON;AUX_LED_BLUE_ON;}
		if (led == 5) {AUX_LED_RED_OFF;AUX_LED_GREEN_OFF;AUX_LED_BLUE_ON;}
		if (led == 6) {AUX_LED_RED_ON;AUX_LED_GREEN_OFF;AUX_LED_BLUE_ON;}
		if (led == 7) {AUX_LED_RED_ON;AUX_LED_GREEN_ON;AUX_LED_BLUE_ON;}
	}
}

uint8_t pp6_get_aux_led(pocket_piano *pp6) {
	return pp6->aux_led;
}

// LED flashing
void pp6_flash_mode_led(pocket_piano *pp6, uint8_t flash_time) {
	pp6->mode_led_flash = flash_time;
}

void pp6_flash_aux_led(pocket_piano *pp6, uint8_t flash_time) {
	pp6->aux_led_flash = flash_time;
}

void pp6_flash_update(pocket_piano *pp6) {

	if (pp6->aux_led_flash) {
		AUX_LED_RED_ON;AUX_LED_GREEN_ON;AUX_LED_BLUE_ON;
		pp6->aux_led_flash--;
		if (pp6->aux_led_flash == 0) {
			pp6_set_aux_led(pp6, pp6->aux_led);
		}
	}

	if (pp6->mode_led_flash) {
		MODE_LED_RED_ON;MODE_LED_GREEN_ON;MODE_LED_BLUE_ON;
		pp6->mode_led_flash--;
		if (pp6->mode_led_flash == 0) {
			pp6_set_mode_led(pp6, pp6->mode_led);
		}
	}
}

// key scanning and assignment, this must be called after pp6_keys_update()
void pp6_get_key_events(pocket_piano *pp6) {


	uint32_t i;

	// scan keys 16 keys


	pp6->num_keys_down = 0;
	for (i = 0; i < 41; i++) {   // the first 41 are keyboard keys
		if ( pp6->keys[i] ) {
			pp6->num_keys_down++;
		}
		if ( pp6->keys[i] &&  !pp6->keys_last[i]  )  {  // new key down
			pp6_set_note_on(pp6, i + 36);   // keyboard starts at midi note 36
			pp6_inc_physical_notes_on(pp6);
		}
		if ( !pp6->keys[i] &&  pp6->keys_last[i]   )  {  // key up
			pp6_set_note_off(pp6, i + 36);   // keyboard starts at midi note 36
			pp6_dec_physical_notes_on(pp6);
		}
	}

	// check mode and aux button  (we only care about a mode press, but need press and release events for aux button)
	if ( pp6->keys[41] &&  !pp6->keys_last[41]){
		pp6_set_mode_button_pressed(pp6);
	}
	if ( pp6->keys[42] && !pp6->keys_last[42]){
		pp6_set_aux_button_pressed(pp6);
	}
	if ( !pp6->keys[42] && pp6->keys_last[42]){
		pp6_set_aux_button_released(pp6);
	}

	for (i = 0; i<43; i++){
		pp6->keys_last[i] = pp6->keys[i];
	}
}

// the note interface for the piano
void pp6_allocate_voices(pocket_piano *pp6){
	uint8_t i, j, already_playing = 0;

	// loop over the keys
	for (i = 0; i < 128; i++) {
		// if the key is up
		if (!pp6_get_note_state(pp6, i)){
		   // check if we need to stop that key
		   for (j=0; j < 4; j++){
				if (pp6->voices[j] == i) pp6->voices[j] = 0;
		   }
		}
		// if its down
		else {
			// see that its not already playing
			already_playing = 0;
			for (j=0; j < 4; j++) {
				if ( pp6->voices[j] == i ) already_playing = 1;
			}
			// if its not, try to allocate
			if (!already_playing){
				for (j=0; j < 4; j++) {
					if (pp6->voices[j] == 0) {
						pp6->voices[j] = i ;
						break;
					}
				}
			}
		}
	} // looping over keys
}

void pp6_set_note_off(pocket_piano *pp6, uint8_t note){
	pp6->note_state[note & 0x7f] = 0;
}
void pp6_set_note_on(pocket_piano *pp6, uint8_t note){
	pp6->note_state[note & 0x7f] = 1;
}
uint8_t pp6_get_note_state(pocket_piano *pp6, uint8_t note){
	return pp6->note_state[note & 0x7f];
}
uint8_t pp6_get_note_state_last(pocket_piano *pp6, uint8_t note){
	return pp6->note_state_last[note & 0x7f];
}
void pp6_set_current_note_state_to_last(pocket_piano *pp6){
	uint8_t i;
	for (i = 0; i < 128; i++){
		pp6->note_state_last[i] = pp6->note_state[i];
	}
}
void pp6_turn_off_all_on_notes(pocket_piano *pp6) {
	uint8_t i;
	for (i = 0; i < 128; i++){
		if (pp6->note_state[i]) {
			pp6->note_state[i] = 0;
		}
	}
}



//MIDI Events
void pp6_set_midi_start(pocket_piano *pp6) {
	pp6->midi_start_flag = 1;
	pp6->midi_clock_tick_count = 0;
}
uint8_t pp6_get_midi_start(pocket_piano *pp6){
	return pp6->midi_start_flag;
}
void pp6_set_midi_stop(pocket_piano *pp6) {
	pp6->midi_stop_flag = 1;
}
uint8_t pp6_get_midi_stop(pocket_piano *pp6){
	return pp6->midi_stop_flag;
}

void pp6_clear_flags(pocket_piano *pp6){

	pp6->aux_button_pressed = 0;
	pp6->aux_button_released = 0;
	pp6->mode_button_pressed = 0;
	pp6->mode_button_released = 0;
	pp6->knob_touched[0] = 0;
	pp6->knob_touched[1] = 0;
	pp6->knob_touched[2] = 0;
	pp6->midi_start_flag = 0;
	pp6->midi_stop_flag = 0;
	pp6->midi_clock_flag = 0;


}

uint8_t pp6_get_num_keys_down(pocket_piano *pp6){
	return pp6->num_keys_down;
}

void pp6_inc_physical_notes_on(pocket_piano *pp6){
	pp6->physical_notes_on++;
}
void pp6_dec_physical_notes_on(pocket_piano *pp6){
	if (pp6->physical_notes_on) pp6->physical_notes_on--;   // check it is positive in case it turns on while a key is pressed or during midi note
}

uint8_t pp6_get_physical_notes_on(pocket_piano *pp6){
	return pp6->physical_notes_on;
}

/**
  * @brief  ADC3 channel12 with DMA configuration
  * @param  None
  * @retval None
  */
void pp6_knobs_init(pocket_piano *pp6)
{
}

void pp6_knobs_update(pocket_piano *pp6) {
}


// this should be called every half second or so
void pp6_check_knobs_touched (pocket_piano *pp6) {
	static float knobs_last[3] = {0, 0, 0};

	if (ABS(pp6->knob[0] - knobs_last[0]) > .1f) {
		pp6->knob_touched[0] = 1;
		knobs_last[0] = pp6->knob[0];
	}

	if (ABS(pp6->knob[1] - knobs_last[1]) > .1f) {
		pp6->knob_touched[1] = 1;
		knobs_last[1] = pp6->knob[1];
	}

	if (ABS(pp6->knob[2] - knobs_last[2]) > .1f) {
		pp6->knob_touched[2] = 1;
		knobs_last[2] = pp6->knob[2];
	}
}

uint8_t pp6_any_knobs_touched(pocket_piano *pp6) {
	if (pp6->knob_touched[0] || pp6->knob_touched[1] || pp6->knob_touched[2])
		return 1;
	else
		return 0;
}
uint8_t pp6_knob_1_touched(pocket_piano *pp6){
	return pp6->knob_touched[0];
}
uint8_t pp6_knob_2_touched(pocket_piano *pp6){
	return pp6->knob_touched[1];
}
uint8_t pp6_knob_3_touched(pocket_piano *pp6){
	return pp6->knob_touched[2];
}

void pp6_smooth_knobs(pocket_piano *pp6){


	static float knob1 = 0;
	static float knob2 = 0;
	static float knob3 = 0;
	float kFilteringFactor = .05f; // the smoothing factor 1 is no smoothing

	knob1 = (pp6->knob[0] * kFilteringFactor) + (knob1 * (1.0 - kFilteringFactor));
	pp6->knob[0] = knob1;

	knob2 = (pp6->knob[1] * kFilteringFactor) + (knob2 * (1.0 - kFilteringFactor));
	pp6->knob[1] = knob2;

	knob3 = (pp6->knob[2] * kFilteringFactor) + (knob3 * (1.0 - kFilteringFactor));
	pp6->knob[2] = knob3;
}





void pp6_leds_init(pocket_piano *pp6) {

}



void pp6_keys_init(pocket_piano *pp6) {
}


void pp6_keys_update(pocket_piano *pp6){

	// debouncem
/*	for (i = 0; i < 43; i++) {
	    if ((pp6->keys_history[0][i] == pp6->keys_history[1][i])
				&& (pp6->keys_history[0][i] == pp6->keys_history[2][i])
				&& (pp6->keys_history[0][i] == pp6->keys_history[3][i])) {
			pp6->keys[i] = pp6->keys_history[0][i];
		}
	}*/
}
