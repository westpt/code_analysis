/**
 * @file timer_internal.c
 * @brief 定时器系统内部函数实现
 *
 * 该文件实现了定时器系统的内部函数，仅供内部实现使用。
 */

#include "timer_internal.h"
#include <stdlib.h>

/**
 * @brief 查找指定ID的定时器
 */
Timer* find_timer(TimerSystem* system, uint32_t id) {
    if (system == NULL) {
        return NULL;
    }
    
    Timer* current = system->head;
    while (current != NULL) {
        if (current->id == id) {
            return current;
        }
        current = current->next;
    }
    return NULL;
}