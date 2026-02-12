/*
 * line.h
 *
 *  Created on: Apr 18, 2012
 *      Author: owen
 */

#ifndef LINE_H_
#define LINE_H_
#include <stdint.h>
#include "audio.h"

typedef struct {
	float target;
	float value;
	float step_slope;
	uint32_t num_steps;
	uint32_t steps_remain;
} line;

void line_set(line * l, float v);
void line_go(line * l, float v, float t);
float line_process(line * line);
uint32_t line_is_processing(line * line);

//float line_multi(float * pairs, uint32_t num_segments);

#endif /* LINE_H_ */
