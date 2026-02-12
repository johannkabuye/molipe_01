/*
 * sawtooth.h
 *
 *  Created on: Apr 1, 2012
 *      Author: owen
 */

#ifndef OSCILLATOR_H_
#define OSCILLATOR_H_

#include <stdint.h>

typedef struct {
	float freq;
	int32_t phase;
	uint32_t phase_step;
} phasor;

typedef struct {
	float freq;
	float amplitude;
	int32_t phase;
	uint32_t phase_step;
} sawtooth_oscillator;

typedef struct {
	float freq;
	float amplitude;
	int32_t phase;
	uint32_t phase_step;
} square_oscillator;

typedef struct {
	float freq;
	float amplitude;
	float amplitude_target;
	int32_t phase;
	uint32_t phase_step;
	uint32_t phase_accum;
} sin_oscillator;

typedef struct {
	float freq;
	int32_t phase;
	uint32_t phase_step;
} bl_saw;

typedef struct {
	float freq;
	int32_t phase_1;
	int32_t phase_2;
	uint32_t phase_step;
} bl_square;

typedef struct {
	uint32_t modulator_phase_accum;
	uint32_t carrier_phase_accum;
	uint32_t modulator_phase;
	uint32_t modulator_phase_step;
	uint32_t carrier_phase;
	int32_t carrier_phase_step; // this is a signed int because its sometimes negative frequency
} FM_oscillator;


// 0 - 1 phasor
void phasor_set(phasor * p, float freq);
float phasor_process(phasor * p);

// basic sawtooth oscillator
void sawtooth_set(sawtooth_oscillator * saw, float freq, float amp);
float sawtooth_process(sawtooth_oscillator * saw);

// square wave
void squarewave_set(square_oscillator * square, float freq, float amp);
float squarewave_process(square_oscillator * square);

// sine oscillator
void sin_init(sin_oscillator * oscil);
void sin_set(sin_oscillator * oscil, float freq, float amp);
void sin_reset(sin_oscillator * oscil);
float sin_process(sin_oscillator * oscil, uint8_t wavetable_selector);
float sin_process_simple(sin_oscillator * oscil, uint8_t wavetable_selector);
float arm_sin_f32(float x, uint8_t wavetable_selector);


/////////////////
float simple_sin(float f);
float simple_FM(float freq, float harmonicity, float index);
float FM_oscillator_process (FM_oscillator * fm_osc, float freq, float harmonicity, float index, uint8_t wavetable_selector);



//////////////
float bl_step_table_read(float index);
float bl_saw_process(bl_saw * saw);
void bl_saw_set(bl_saw * saw, float freq);
void bl_saw_reset(bl_saw * saw);


float bl_square_process(bl_square * square);
void bl_square_set(bl_square * square, float freq);
void bl_square_init(bl_square * square);


#endif /* SAWTOOTH_H_ */
