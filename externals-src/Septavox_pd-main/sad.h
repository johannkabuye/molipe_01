/*
 * sad.h
 *
 *  Created on: Jul 4, 2012
 *      Author: owen
 */

#ifndef SAD_H_
#define SAD_H_

#include <stdint.h>
#include "audio.h"

typedef struct {
	float val;
	float attack_time;
	float decay_time;
	float attack_delta;
	float decay_delta;
	float stop_delta;
	uint8_t segment;
} sad;

void sad_init(sad * sad);
float sad_process(sad * sad);
void sad_set(sad * sad, float a, float d);
void sad_go(sad * sad);

#endif /* SAD_H_ */
