/**
 * @file timer_internal.h
 * @brief 定时器系统内部函数声明
 *
 * 该头文件声明了定时器系统的内部函数和数据结构，仅供内部实现使用。
 */

#ifndef TIMER_INTERNAL_H
#define TIMER_INTERNAL_H

#include "../include/timer.h"

/**
 * @brief 查找指定ID的定时器
 * 
 * @param system 定时器系统指针
 * @param id 定时器ID
 * @return 找到的定时器指针，如果未找到则返回NULL
 */
Timer* find_timer(TimerSystem* system, uint32_t id);

#endif /* TIMER_INTERNAL_H */