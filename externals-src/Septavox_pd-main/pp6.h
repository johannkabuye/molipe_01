/*
 * pp6.h
 *
 *  Created on: Jun 23, 2012
 *      Author: owen
 */

#ifndef PP6_H_
#define PP6_H_

#include "oscillator.h"
#include "sadsr.h"
#include "sad.h"
#include "line.h"

#define MODE_LED_BLUE_ON 
#define MODE_LED_RED_ON 
#define MODE_LED_GREEN_ON
#define MODE_LED_BLUE_OFF
#define MODE_LED_RED_OFF
#define MODE_LED_GREEN_OFF

#define AUX_LED_BLUE_ON 
#define AUX_LED_RED_ON 
#define AUX_LED_GREEN_ON 
#define AUX_LED_BLUE_OFF 
#define AUX_LED_RED_OFF 
#define AUX_LED_GREEN_OFF 

#define BLACK 0
#define RED 1
#define YELLOW 2
#define GREEN 3
#define CYAN 4
#define BLUE 5
#define MAGENTA 6

#define MIDI_CLOCK_TIMEOUT 20000  // around 1 second of not receiving midi clock


typedef struct {

	// global transpose
	uint8_t oct_transpose;   // 0 is no transpose

	// knobs
	uint8_t knob_touched[3]; 	// flag to see if knob is touched
	float knob[3];   		// stores knob values 0-1

	// secret mode
	uint8_t secret_mode_enabled;

	// freqs and amps that are shared between all modes

    // voices the synth is playing
	uint8_t voices[4];
	uint8_t voices_last[4];
	uint8_t voices_note_on_flag[4];  // 4 flags for new notes

	uint8_t physical_notes_on;    // the number of non sequenced notes currently on
	uint8_t note_state[128];	  // state of all the midi notes -- 0 for off, anything else for on
	uint8_t note_state_last[128]; // the previos time thru the main loop that notes were updated.  compared with above to get note events

	// keys
	uint8_t keys[43];
	uint8_t keys_last[43];
	uint8_t keys_history[4][43];
	uint8_t num_keys_down;

	// current mode
	uint32_t mode;

	// mode and aux button event flags
	uint8_t mode_button_pressed;	// mode button event flags
	uint8_t mode_button_released;
	uint8_t aux_button_pressed;		// aux button event flags
	uint8_t aux_button_released;

	uint8_t aux_button_count;

	// LEDs
	uint8_t mode_led;
	uint8_t aux_led;
	uint8_t aux_led_flash; 			// these count down to zero, then the flash is over
	uint8_t mode_led_flash;

	// MIDI clock
	uint8_t midi_start_flag;        // midi start command
	uint8_t midi_stop_flag;    		// midi stop command
	uint32_t midi_in_clock_last;   // stores the system time of the last received midi clock
	uint8_t midi_clock_present;  // if a midi clock is currently present
	uint32_t midi_clock_period;  // time in between midi clock ticks
	uint8_t midi_clock_tick_count;
	uint8_t midi_clock_flag;


    // septavox data
    sin_oscillator wave_synth_sins[4];
    bl_saw wave_synth_saws[4];
    bl_square wave_synth_squares[4];
	float freqs[4];
	float amps[4];
    uint8_t wavetable_selector;

    sadsr mode_adsr_amp_env[4];

    sad mode_octave_arp_amp_env[4];
    uint32_t mode_octave_arp_click;
    uint32_t mode_octave_arp_click_count;
    uint8_t mode_octave_arp_l;
    uint8_t mode_octave_arp_octave_shift;
    uint8_t mode_octave_arp_midi_clk_last;

    line mode_simple_poly_aramps[4];
    sin_oscillator mode_simple_poly_sin_lfo;
    float mode_simple_poly_freqs[4];
    uint8_t mode_simple_poly_voices_last[4];

    line mode_mega_wave_framps[4];
    line mode_mega_wave_aramps[4];
    sin_oscillator mode_mega_wave_waves[4][4];
    float mode_mega_wave_freqs[4][4];
    float mode_mega_wave_amps[4];
	uint8_t mode_mega_wave_voices_last[4];
        
    sad mode_octave_cascade_amp_env[4];
    bl_saw mode_octave_cascade_saws[4];
    bl_square mode_octave_cascade_squares[4];
    uint32_t  mode_octave_cascade_click;
    uint32_t mode_octave_cascade_click_count;
    uint8_t mode_octave_cascade_l;
	uint8_t mode_octave_cascade_count2;
	uint8_t mode_octave_cascade_octave_shift[4];
    uint8_t mode_octave_cascade_midi_clk_last;

    line mode_slicer_aramps[4];
    float mode_slicer_freqs[4];
    float mode_slicer_amps[4];
    uint32_t mode_slicer_step;
    uint32_t mode_slicer_sample_counter;
    uint8_t mode_slicer_slice_amp;
    uint8_t mode_slicer_slice_amp_last;
    line mode_slicer_slice_line;
    float mode_slicer_sliced;
    uint8_t mode_slicer_voices_last[4];

    sadsr mode_slider_amp_env[4];
    uint8_t mode_slider_voices_last[4];
    uint32_t mode_slider_note_dur[4];
    line mode_slider_framps[4];

} pocket_piano;

void pp6_init(pocket_piano *pp6);

void pp6_set_global_octave_transpose(pocket_piano *pp6, uint8_t);
void pp6_enable_secret_mode(pocket_piano *pp6);

float pp6_get_knob_1(pocket_piano *pp6);
float pp6_get_knob_1_raw(pocket_piano *pp6);
float pp6_get_knob_2(pocket_piano *pp6);
float pp6_get_knob_3(pocket_piano *pp6);
void pp6_set_knob_1(pocket_piano *pp6,float v);
void pp6_set_knob_2(pocket_piano *pp6,float v);
void pp6_set_knob_3(pocket_piano *pp6,float v);
float * pp6_get_knob_array(pocket_piano *pp6);
void pp6_set_knob_array(pocket_piano *pp6,float * knobs);
void pp6_check_knobs_touched (pocket_piano *pp6);
uint8_t pp6_any_knobs_touched(pocket_piano *pp6);
uint8_t pp6_knob_1_touched(pocket_piano *pp6);
uint8_t pp6_knob_2_touched(pocket_piano *pp6);
uint8_t pp6_knob_3_touched(pocket_piano *pp6);

uint8_t pp6_get_synth_note_start(pocket_piano *pp6);
void pp6_set_synth_note_start (pocket_piano *pp6);
uint8_t pp6_get_synth_note_stop(pocket_piano *pp6);
void pp6_set_synth_note_stop (pocket_piano *pp6);
uint8_t pp6_get_synth_note(pocket_piano *pp6);
void pp6_set_synth_note(pocket_piano *pp6,uint8_t note);


void pp6_clear_flags(pocket_piano *pp6);

uint8_t pp6_is_playing (pocket_piano *pp6);

uint8_t pp6_get_num_keys_down(pocket_piano *pp6);
void pp6_get_key_events(pocket_piano *pp6);  // checks keys for new events
void pp6_allocate_voices(pocket_piano *pp6);

void pp6_change_mode(pocket_piano *pp6);
uint32_t pp6_get_mode(pocket_piano *pp6);
void pp6_set_mode(pocket_piano *pp6,uint32_t mode);

void pp6_keys_init(pocket_piano *pp6);
void pp6_keys_update(pocket_piano *pp6);   // scans and debounces keys
void pp6_leds_init(pocket_piano *pp6);
void pp6_leds_update(pocket_piano *pp6,uint8_t bank_led, uint8_t mode_led);
void pp6_knobs_init(pocket_piano *pp6);
void pp6_knobs_update(pocket_piano *pp6);
void pp6_smooth_knobs(pocket_piano *pp6);

uint8_t pp6_get_mode_led(pocket_piano *pp6);
uint8_t pp6_get_aux_led(pocket_piano *pp6);
void pp6_set_mode_led(pocket_piano *pp6,uint8_t mode_led);
void pp6_set_aux_led(pocket_piano *pp6,uint8_t bank_led);

void pp6_flash_mode_led(pocket_piano *pp6,uint8_t flash_time);
void pp6_flash_aux_led(pocket_piano *pp6,uint8_t flash_time);
void pp6_flash_update(pocket_piano *pp6);

void  pp6_set_mode_button_pressed(pocket_piano *pp6);
void pp6_set_mode_button_released(pocket_piano *pp6);
uint8_t pp6_mode_button_pressed(pocket_piano *pp6);
uint8_t pp6_mode_button_released(pocket_piano *pp6);

void  pp6_set_aux_button_pressed(pocket_piano *pp6);
void pp6_set_aux_button_released(pocket_piano *pp6);
uint8_t pp6_aux_button_pressed(pocket_piano *pp6);
uint8_t pp6_aux_button_released(pocket_piano *pp6);

void pp6_inc_physical_notes_on(pocket_piano *pp6);
void pp6_dec_physical_notes_on(pocket_piano *pp6);
uint8_t pp6_get_physical_notes_on(pocket_piano *pp6);

// midi start stop events
void pp6_set_midi_start(pocket_piano *pp6);
uint8_t pp6_get_midi_start(pocket_piano *pp6);
void pp6_set_midi_stop(pocket_piano *pp6);
uint8_t pp6_get_midi_stop(pocket_piano *pp6);

/// MIDI clock stuff
void pp6_midi_clock_tick(pocket_piano *pp6);
void pp6_check_for_midi_clock(pocket_piano *pp6) ;
uint8_t pp6_midi_clock_present(pocket_piano *pp6);
uint32_t pp6_get_midi_clock_period(pocket_piano *pp6);
uint8_t pp6_get_midi_clock_tick(pocket_piano *pp6);
void pp6_clear_midi_clock_tick(pocket_piano *pp6);
uint8_t pp6_get_midi_clock_count(pocket_piano *pp6) ;

// the note interface for the piano
uint8_t pp6_note_on_flag(pocket_piano *pp6);
uint8_t pp6_note_off_flag(pocket_piano *pp6);
void pp6_set_note_off(pocket_piano *pp6,uint8_t note);
void pp6_set_note_on(pocket_piano *pp6,uint8_t note);
uint8_t pp6_get_note_state(pocket_piano *pp6,uint8_t note);
uint8_t pp6_get_note_state_last(pocket_piano *pp6,uint8_t);
void pp6_set_current_note_state_to_last(pocket_piano *pp6);
void pp6_turn_off_all_on_notes(pocket_piano *pp6);

#endif /* PP6_H_ */
