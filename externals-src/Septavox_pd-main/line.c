/*
 * line.c
 *
 *  Created on: Apr 18, 2012
 *      Author: owen
 */
#include <stdint.h>
#include "line.h"

void line_set(line * l, float v){
	l->value = v;
}

void line_go(line * line, float v, float t){

	line->target = v;

	line->num_steps = (t / 1000.f) * SR;

	// ammount i'm stepping
	line->step_slope = (line->target - line->value) / (float)line->num_steps;

	// reset the step countdown
	line->steps_remain = line->num_steps;

}

float line_process(line * line){

	if (line->steps_remain) {
		line->value += line->step_slope;
		line->steps_remain--;
	}
	if (line->steps_remain == 0) {
		line->value = line->target;
	}

	return line->value;
}
