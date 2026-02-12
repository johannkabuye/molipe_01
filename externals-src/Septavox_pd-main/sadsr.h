/*
 * sadsr.h
 *
 *  Created on: Jul 4, 2012
 *      Author: owen
 */

#ifndef SADSR_H_
#define SADSR_H_

#include <stdint.h>
#include "audio.h"

typedef struct {
	float val;
	float attack_delta;
	float decay_delta;
	float release_delta;
	float sustain_level;
	float stop_delta;
	uint8_t segment;
	uint8_t zero_flag;
} sadsr;

void sadsr_init(sadsr * sadsr);

float sadsr_process(sadsr * sadsr);

void sadsr_set(sadsr * sadsr, float a, float d, float r, float sus_level);

void sadsr_go(sadsr * sadsr);
void sadsr_release(sadsr * sadsr);


uint8_t sadsr_zero_flag(sadsr * sadsr);

#endif /* SADSR_H_ */
