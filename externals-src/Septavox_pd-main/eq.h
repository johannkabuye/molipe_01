/*
 * eq.h
 *
 *  Created on: Aug 21, 2012
 *      Author: owen
 */

#ifndef EQ_H_
#define EQ_H_

#ifndef PI
#define PI 3.14159265359f
#endif

#include "arm_math.h"



// ------------
//| Structures |
// ------------

typedef struct
{
// Filter #1 (Low band)

float32_t lf; // Frequency
float32_t f1p0; // Poles ...
float32_t f1p1;
float32_t f1p2;
float32_t f1p3;

// Filter #2 (High band)

float32_t hf; // Frequency
float32_t f2p0; // Poles ...
float32_t f2p1;
float32_t f2p2;
float32_t f2p3;

// Sample history buffer

float32_t sdm1; // Sample data minus 1
float32_t sdm2; // 2
float32_t sdm3; // 3

// Gain Controls

float32_t lg; // low gain
float32_t mg; // mid gain
float32_t hg; // high gain

} EQSTATE;


// ---------
//| Exports |
// ---------

void init_3band_state(EQSTATE* es, int32_t lowfreq, int32_t highfreq, int32_t mixfreq);
float32_t do_3band(EQSTATE* es, float32_t sample);



#endif /* EQ_H_ */
