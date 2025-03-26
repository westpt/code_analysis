/**
 * @file timer.c
 * @brief 定时器协程系统实现文件
 *
 * 该文件实现了定时器协程系统的所有功能，包括定时器的创建、管理和调度。
 */

#include "../include/timer.h"
#include "../include/timer_internal.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

// 定义静态全局TimerSystem指针
static TimerSystem* g_timer_system = NULL;

/**
 * @brief 初始化定时器系统
 */
bool timer_system_init(void) {
    if (g_timer_system != NULL) {
        return true;
    }
    
    g_timer_system = (TimerSystem*)malloc(sizeof(TimerSystem));
    if (g_timer_system == NULL) {
        return false;
    }
    
    g_timer_system->head = NULL;
    g_timer_system->next_id = 1;  // ID从1开始，0表示无效ID
    g_timer_system->running = true;
    
    return true;
}

/**
 * @brief 创建一个新的定时器任务
 */
uint32_t timer_create(uint32_t interval, TimerCallback callback, void* arg, bool repeat) {
    if (g_timer_system == NULL || callback == NULL || interval == 0) {
        return 0;
    }
    
    Timer* timer = (Timer*)malloc(sizeof(Timer));
    if (timer == NULL) {
        return 0;
    }
    
    // 初始化定时器
    timer->id = g_timer_system->next_id++;
    timer->interval = interval;
    timer->remaining = interval;
    timer->repeat = repeat;
    timer->state = TIMER_IDLE;
    timer->callback = callback;
    timer->arg = arg;
    timer->next = NULL;
    
    // 添加到链表头部
    if (g_timer_system->head == NULL) {
        g_timer_system->head = timer;
    } else {
        timer->next = g_timer_system->head;
        g_timer_system->head = timer;
    }
    
    return timer->id;
}

/**
 * @brief 启动定时器任务
 */
bool timer_start(uint32_t id) {
    if (g_timer_system == NULL) {
        return false;
    }
    
    Timer* timer = find_timer(g_timer_system, id);
    if (timer == NULL) {
        return false;
    }
    
    if (timer->state != TIMER_RUNNING) {
        timer->state = TIMER_RUNNING;
        return true;
    }
    
    return false;  // 已经在运行中
}

/**
 * @brief 暂停定时器任务
 */
bool timer_pause(uint32_t id) {
    if (g_timer_system == NULL) {
        return false;
    }
    
    Timer* timer = find_timer(g_timer_system, id);
    if (timer == NULL) {
        return false;
    }
    
    if (timer->state == TIMER_RUNNING) {
        timer->state = TIMER_PAUSED;
        return true;
    }
    
    return false;  // 不在运行中
}

/**
 * @brief 取消定时器任务
 */
bool timer_cancel(uint32_t id) {
    if (g_timer_system == NULL) {
        return false;
    }
    
    Timer* current = g_timer_system->head;
    Timer* prev = NULL;
    
    while (current != NULL) {
        if (current->id == id) {
            // 从链表中移除
            if (prev == NULL) {
                g_timer_system->head = current->next;
            } else {
                prev->next = current->next;
            }
            
            free(current);
            return true;
        }
        
        prev = current;
        current = current->next;
    }
    
    return false;  // 未找到定时器
}

/**
 * @brief 更新定时器系统，处理到期的定时器任务
 */
void timer_update(uint32_t elapsed) {
    if (g_timer_system == NULL || !g_timer_system->running) {
        return;
    }
    
    Timer* current = g_timer_system->head;
    Timer* prev = NULL;
    
    while (current != NULL) {
        Timer* next = current->next;  // 保存下一个节点，因为当前节点可能被删除
        
        if (current->state == TIMER_RUNNING) {
            if (current->remaining <= elapsed) {
                // 定时器到期，执行回调
                current->callback(current->arg);
                
                if (current->repeat) {
                    // 重复执行的定时器，重置剩余时间
                    current->remaining = current->interval;
                } else {
                    // 非重复执行的定时器，从链表中移除
                    if (prev == NULL) {
                        g_timer_system->head = current->next;
                    } else {
                        prev->next = current->next;
                    }
                    
                    free(current);
                    current = next;
                    continue;
                }
            } else {
                // 更新剩余时间
                current->remaining -= elapsed;
            }
        }
        
        prev = current;
        current = next;
    }
}

/**
 * @brief 销毁定时器系统，释放所有资源
 */
void timer_system_destroy(void) {
    if (g_timer_system == NULL) {
        return;
    }
    
    // 释放所有定时器
    Timer* current = g_timer_system->head;
    while (current != NULL) {
        Timer* next = current->next;
        free(current);
        current = next;
    }
    
    // 释放系统结构
    free(g_timer_system);
    g_timer_system = NULL;
}

/**
 * @brief 获取定时器系统中的定时器数量
 */
uint32_t timer_count(void) {
    if (g_timer_system == NULL) {
        return 0;
    }
    
    uint32_t count = 0;
    Timer* current = g_timer_system->head;
    
    while (current != NULL) {
        count++;
        current = current->next;
    }
    
    return count;
}