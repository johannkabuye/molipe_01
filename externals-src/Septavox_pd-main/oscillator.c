/*
 *
 *  Created on: Apr 1, 2012
 *      Author: owen
 */

#include <stdint.h>
#include "audio.h"
#include "oscillator.h"
#include "waves.h"

#define PI 3.14159265359f


/*
 * phasor oscillator
 */
void phasor_set(phasor * p, float freq) {
	p->phase_step = (uint32_t) (freq * (2147483648.0f / SR));
}

float phasor_process(phasor * p){
	// just let it roll over
	p->phase += p->phase_step;
	return (((float) p->phase / 2147483648.0f) + 1.f) * .5f;
}


/*
 * sawtooth oscillator
 */
void sawtooth_set(sawtooth_oscillator * saw, float freq, float amp) {
	saw->phase_step = (uint32_t) (freq * (2147483648.0f / SR));
	saw->amplitude = amp;
}

float sawtooth_process(sawtooth_oscillator * saw){
	// just let it roll over
	saw->phase += saw->phase_step;
	return ((float) saw->phase / 2147483648.0f) * saw->amplitude;
}

/*
 * square oscillator
 */
void squarewave_set(square_oscillator * square, float freq, float amp) {
	square->phase_step = (uint32_t) (freq * (2147483648.0f / SR));
	square->amplitude = amp;
}

float squarewave_process(square_oscillator * square){
	float squarewave;
	// just let it roll over
	square->phase += square->phase_step;
	if (square->phase > 0) squarewave = 1.0f;
	else squarewave = -1.0f;
	return squarewave * square->amplitude;
}

/*
 * sine oscillator
 */
void sin_init(sin_oscillator * oscil){
	oscil->amplitude = 0.f;
	oscil->freq = 0.f;
	oscil->phase = 0;
	oscil->phase_step = 0;
}

void sin_reset(sin_oscillator * oscil){
	oscil->phase = 0;
}

void sin_set(sin_oscillator * oscil, float freq, float amp){
	if (freq < 0) freq *= -1.f;

	oscil->phase_step = (uint32_t) (freq * (2147483648.0f / SR));
	oscil->amplitude_target = amp;
}

float sin_process(sin_oscillator * oscil, uint8_t wavetable_selector){

	float phase;

	oscil->amplitude = oscil->amplitude_target;
	oscil->phase += oscil->phase_step;
	phase = (((float) oscil->phase / 2147483648.0f) + 1.0f) * PI;

	return arm_sin_f32(phase, wavetable_selector) * oscil->amplitude;

}

float sin_process_simple(sin_oscillator * oscil, uint8_t wavetable_selector){

	uint32_t phase;

	float ym1, y, yp1, yp2, frac;

	phase = ((oscil->phase_accum >> 24) & 0xff) + 1;

	ym1 = sinTable[wavetable_selector][phase - 1];
	y = sinTable[wavetable_selector][phase];
	yp1 = sinTable[wavetable_selector][phase + 1];
	yp2 = sinTable[wavetable_selector][phase + 2];


	frac =  (float) (oscil->phase_accum & 0x00FFFFFF) / 16777216.f;


	oscil->phase_accum += oscil->phase_step;
	return y + frac * (yp1 - y);

}


//////////////

static inline float cube_interp(float fr, float inm1, float
                                in, float inp1, float inp2)
{
	return in + 0.5f * fr * (inp1 - inm1 +
	 fr * (4.0f * inp1 + 2.0f * inm1 - 5.0f * in - inp2 +
	 fr * (3.0f * (in - inp1) - inm1 + inp2)));
}

float simple_sin(float freq) {
	static uint32_t phase_accum;
	uint32_t phase;
	uint32_t phase_step = (uint32_t) (freq * (2147483648.0f / SR));

	float ym1, y, yp1, yp2, frac;

	phase = ((phase_accum >> 24) & 0xff) + 1;

	ym1 = sin_table[phase - 1];
	y = sin_table[phase];
	yp1 = sin_table[phase + 1];
	yp2 = sin_table[phase + 2];

	//ym1 = saw_table[phase - 1];
	//y = saw_table[phase];
	//yp1 = saw_table[phase + 1];
	//yp2 = saw_table[phase + 2];

	frac =  (float) (phase_accum & 0x00FFFFFF) / 16777216.f;


	phase_accum += phase_step;
	return y + frac * (yp1 - y);
	//return cube_interp(frac, ym1, y, yp1, yp2);
}

// single FM
float simple_FM(float freq, float harmonicity, float index) {

	static uint32_t modulator_phase_accum;
	static uint32_t carrier_phase_accum;
	uint32_t modulator_phase;
	uint32_t modulator_phase_step;
	uint32_t carrier_phase;
	int32_t carrier_phase_step; // this is a signed int because its sometimes negative frequency

	float  y, yp1, frac, modulator, carrier;

	// modulator frequency = f * harmonicity
	modulator_phase_step = (uint32_t) (freq * (2147483648.0f / SR) * harmonicity);

	modulator_phase = ((modulator_phase_accum >> 24) & 0xff) + 1;
	y = sin_table[modulator_phase];
	yp1 = sin_table[modulator_phase + 1];
	frac =  (float) (modulator_phase_accum & 0x00FFFFFF) / 16777216.f;
	modulator_phase_accum += modulator_phase_step;
	modulator = y + frac * (yp1 - y);

	// scale it with index (deviation = mod freq * index)
	modulator *= harmonicity * freq * index;

	// do the fm
	freq += modulator;

	// compute carrier freq
	carrier_phase_step = (int32_t) (freq * (2147483648.0f / SR)) + (int32_t)(modulator * (2147483648.0f / SR));

	// carrier oscillator
	carrier_phase = ((carrier_phase_accum >> 24) & 0xff) + 1;
	y = sin_table[carrier_phase];
	yp1 = sin_table[carrier_phase + 1];
	frac =  (float) (carrier_phase_accum & 0x00FFFFFF) / 16777216.f;
	carrier_phase_accum += carrier_phase_step;

	// interpolate
	carrier = y + frac * (yp1 - y);

	return carrier;
}

float FM_oscillator_process (FM_oscillator * fm_osc, float freq, float harmonicity, float index, uint8_t wavetable_selector) {


	float  y, yp1, frac, modulator, carrier;

	// modulator frequency = f * harmonicity
	fm_osc->modulator_phase_step = (uint32_t) (freq * (2147483648.0f / SR) * harmonicity);

	fm_osc->modulator_phase = ((fm_osc->modulator_phase_accum >> 24) & 0xff) + 1;
	y = sinTable[0][fm_osc->modulator_phase];
	yp1 = sinTable[0][fm_osc->modulator_phase + 1];
	frac =  (float) (fm_osc->modulator_phase_accum & 0x00FFFFFF) / 16777216.f;
	fm_osc->modulator_phase_accum += fm_osc->modulator_phase_step;
	modulator = y + frac * (yp1 - y);

	// scale it with index (deviation = mod freq * index)
	modulator *= harmonicity * freq * index;

	// do the fm
	freq += modulator;

	// compute carrier freq
	fm_osc->carrier_phase_step = (int32_t) (freq * (2147483648.0f / SR)) + (int32_t)(modulator * (2147483648.0f / SR));

	// carrier oscillator
	fm_osc->carrier_phase = ((fm_osc->carrier_phase_accum >> 24) & 0xff) + 1;
	y = sinTable[wavetable_selector][fm_osc->carrier_phase];
	yp1 = sinTable[wavetable_selector][fm_osc->carrier_phase + 1];
	frac =  (float) (fm_osc->carrier_phase_accum & 0x00FFFFFF) / 16777216.f;
	fm_osc->carrier_phase_accum += fm_osc->carrier_phase_step;

	// interpolate
	carrier = y + frac * (yp1 - y);

	return carrier;
}

//TODO : it seems these bl oscillators can't handle a 0 freq  (since it would ential a divide by 0),  so maybe check for 0 freq

// step table, floating index
float bl_step_table_read(float index) {
	uint32_t table_index;
	float frac;
	float y, yp1;

	table_index = (uint32_t) index;

	frac = (float) table_index - index;

	y = transition_table[table_index];
	yp1 = transition_table[table_index + 1];
	return y + frac * (yp1 - y);
}

void bl_saw_set(bl_saw * saw, float freq) {
	saw->phase_step = (uint32_t) (freq * (2147483648.0f / SR));
	saw->freq = freq;
}

void bl_saw_reset(bl_saw * saw){
	saw->phase = 0;
}

// from PD patch, transition table is used for the step
float bl_saw_process(bl_saw * saw){

	float sig;
	float transition_table_index;

	saw->phase += saw->phase_step;
	sig = ((((float) saw->phase / 2147483648.0f) + 1.f) * .5f) - .5f;
	//sig -= .5f;

	// scale it, numerator controls the band limit
	transition_table_index = sig * ((SR * .3) / saw->freq);
	// clip it
	if (transition_table_index > .5f) transition_table_index = .5f;
	if (transition_table_index < -.5f) transition_table_index = -.5f;
	// range it for transistion table
	transition_table_index *= 1000.f;
	transition_table_index += 501.f;

	// transition tabled is railed, so siq passes through, except during the step
	return bl_step_table_read(transition_table_index) - sig;
}

void bl_square_set(bl_square * square, float freq){
	square->phase_step = (uint32_t) (freq * (2147483648.0f / SR));
	square->freq = freq;
	square->phase_2 = square->phase_1 + 1073741824;   // make the 2 phases 180 out here
}

// this has to be called to set the two saw waves 180 out of phase
//  why isn't this working,  setting both to 0, and when freq is set, they are also set out of phase
void bl_square_init(bl_square * square) {
	// phases must be reset (or do they?)
	square->phase_1 = 0;
	square->phase_2 = 0;//1073741824; // the ratio could also be set for PWM
}

// computes 2 bl saw waves 180 out of phase, and adds them together
float bl_square_process(bl_square * square){
	float sig, saw_1, saw_2;
	float transition_table_index;

	square->phase_1 += square->phase_step;
	sig = ((((float) square->phase_1 / 2147483648.0f) + 1.f) * .5f) - .5f;
	// scale it,  numerator controls the band limit
	transition_table_index = sig * ((SR * .3) / square->freq); 
	// clip it
	if (transition_table_index > .5f) transition_table_index = .5f;
	if (transition_table_index < -.5f) transition_table_index = -.5f;
	// range it for transistion table
	transition_table_index *= 1000.f;
	transition_table_index += 501.f;
	saw_1 = bl_step_table_read(transition_table_index) - sig;

	square->phase_2 += square->phase_step;
	sig = ((((float) square->phase_2 / 2147483648.0f) + 1.f) * .5f) - .5f;
	// scale it
	transition_table_index = sig * (5000.f / square->freq); // 4410 is nyquist * .4
	// clip it,  numerator controls the band limit
	if (transition_table_index > .5f) transition_table_index = .5f;
	if (transition_table_index < -.5f) transition_table_index = -.5f;
	// range it for transistion table
	transition_table_index *= 1000.f;
	transition_table_index += 501.f;
	saw_2 = bl_step_table_read(transition_table_index) - sig;

	return saw_1 + saw_2;
}




/////////////////////


/**
 * @ingroup groupFastMath
 */

/**
 * @defgroup sin Sine
 *
 * Computes the trigonometric sine function using a combination of table lookup
 * and cubic interpolation.  There are separate functions for
 * Q15, Q31, and floating-point data types.
 * The input to the floating-point version is in radians while the
 * fixed-point Q15 and Q31 have a scaled input with the range
 * [0 +0.9999] mapping to [0 2*pi).  The fixed-point range is chosen so that a
 * value of 2*pi wraps around to 0.
 *
 * The implementation is based on table lookup using 256 values together with cubic interpolation.
 * The steps used are:
 *  -# Calculation of the nearest integer table index
 *  -# Fetch the four table values a, b, c, and d
 *  -# Compute the fractional portion (fract) of the table index.
 *  -# Calculation of wa, wb, wc, wd
 *  -# The final result equals <code>a*wa + b*wb + c*wc + d*wd</code>
 *
 * where
 * <pre>
 *    a=Table[index-1];
 *    b=Table[index+0];
 *    c=Table[index+1];
 *    d=Table[index+2];
 * </pre>
 * and
 * <pre>
 *    wa=-(1/6)*fract.^3 + (1/2)*fract.^2 - (1/3)*fract;
 *    wb=(1/2)*fract.^3 - fract.^2 - (1/2)*fract + 1;
 *    wc=-(1/2)*fract.^3+(1/2)*fract.^2+fract;
 *    wd=(1/6)*fract.^3 - (1/6)*fract;
 * </pre>
 */

/**
 * @addtogroup sin
 * @{
 */


/**
 * \par
 * Example code for the generation of the floating-point sine table:
 * <pre>
 * tableSize = 256;
 * for(n = -1; n < (tableSize + 1); n++)
 * {
 *	sinTable[n+1]=sin(2*pi*n/tableSize);
 * }</pre>
 * \par
 * where pi value is  3.14159265358979
 */


/**
 * @brief  Fast approximation to the trigonometric sine function for floating-point data.
 * @param[in] x input value in radians.
 * @return  sin(x).
 */

float arm_sin_f32(float x, uint8_t wavetable_selector)
{

  float sinVal, fract, in;                   /* Temporary variables for input, output */
  int32_t index;                                 /* Index variable */
  uint32_t tableSize = (uint32_t) 259;    /* Initialise tablesize */
  float wa, wb, wc, wd;                      /* Cubic interpolation coefficients */
  float a, b, c, d;                          /* Four nearest output values */
  float *tablePtr;                           /* Pointer to table */
  int32_t n;
  float fractsq, fractby2, fractby6, fractby3, fractsqby2;
  float oneminusfractby2;
  float frby2xfrsq, frby6xfrsq;

  /* input x is in radians */
  /* Scale the input to [0 1] range from [0 2*PI] , divide input by 2*pi */
  in = x * 0.159154943092f;

  /* Calculation of floor value of input */
  n = (int32_t) in;

  /* Make negative values towards -infinity */
  if(x < 0.0f)
  {
    n = n - 1;
  }

  /* Map input value to [0 1] */
  in = in - (float) n;

  /* Calculation of index of the table */
  index = (uint32_t) (tableSize * in);

  /* fractional value calculation */
  fract = ((float) tableSize * in) - (float) index;

  /* Checking min and max index of table */
  if(index < 0)
  {
    index = 0;
  }
  else if(index > 256)
  {
    index = 256;
  }

  /* Initialise table pointer */
  tablePtr = (float *) & sinTable[wavetable_selector][index];

  /* Read four nearest values of input value from the sin table */
  a = tablePtr[0];
  b = tablePtr[1];
  c = tablePtr[2];
  d = tablePtr[3];

  /* Cubic interpolation process */
  fractsq = fract * fract;
  fractby2 = fract * 0.5f;
  fractby6 = fract * 0.166666667f;
  fractby3 = fract * 0.3333333333333f;
  fractsqby2 = fractsq * 0.5f;
  frby2xfrsq = (fractby2) * fractsq;
  frby6xfrsq = (fractby6) * fractsq;
  oneminusfractby2 = 1.0f - fractby2;
  wb = fractsqby2 - fractby3;
  wc = (fractsqby2 + fract);
  wa = wb - frby6xfrsq;
  wb = frby2xfrsq - fractsq;
  sinVal = wa * a;
  wc = wc - frby2xfrsq;
  wd = (frby6xfrsq) - fractby6;
  wb = wb + oneminusfractby2;

  /* Calculate sin value */
  sinVal = (sinVal + (b * wb)) + ((c * wc) + (d * wd));

  /* Return the output value */
  return (sinVal);

}

/**
 * @} end of sin group
 */


