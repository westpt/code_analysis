/**
 * @file timer.h
 * @brief 定时器协程系统头文件
 *
 * 该头文件定义了定时器协程系统的API接口和数据结构，
 * 提供了创建、管理和调度定时器任务的功能。
 */

#ifndef TIMER_H
#define TIMER_H

#include <stdint.h>
#include <stdbool.h>

/**
 * @brief 定时器任务状态枚举
 */
typedef enum {
    TIMER_IDLE,      /**< 空闲状态 */
    TIMER_RUNNING,   /**< 运行状态 */
    TIMER_PAUSED,    /**< 暂停状态 */
    TIMER_COMPLETED  /**< 完成状态 */
} TimerState;

/**
 * @brief 定时器任务回调函数类型
 */
typedef void (*TimerCallback)(void* arg);

/**
 * @brief 定时器任务结构体
 */
typedef struct Timer {
    uint32_t id;              /**< 定时器ID */
    uint32_t interval;        /**< 定时间隔(毫秒) */
    uint32_t remaining;       /**< 剩余时间(毫秒) */
    bool repeat;             /**< 是否重复执行 */
    TimerState state;        /**< 定时器状态 */
    TimerCallback callback;  /**< 回调函数 */
    void* arg;               /**< 回调函数参数 */
    struct Timer* next;      /**< 链表下一个节点 */
} Timer;

/**
 * @brief 定时器系统结构体
 */
typedef struct {
    Timer* head;             /**< 定时器链表头 */
    uint32_t next_id;        /**< 下一个可用的定时器ID */
    bool running;            /**< 系统运行状态 */
} TimerSystem;

/**
 * @brief 初始化定时器系统
 */
void timer_system_init(void);

/**
 * @brief 创建一个新的定时器任务
 * 
 * @param interval 定时间隔(毫秒)
 * @param callback 回调函数
 * @param arg 回调函数参数
 * @param repeat 是否重复执行
 * @return 创建的定时器ID，0表示创建失败
 */
uint32_t timer_create(uint32_t interval, TimerCallback callback, void* arg, bool repeat);

/**
 * @brief 启动定时器任务
 * 
 * @param id 定时器ID
 * @return 是否成功启动
 */
bool timer_start(uint32_t id);

/**
 * @brief 暂停定时器任务
 * 
 * @param id 定时器ID
 * @return 是否成功暂停
 */
bool timer_pause(uint32_t id);

/**
 * @brief 取消定时器任务
 * 
 * @param id 定时器ID
 * @return 是否成功取消
 */
bool timer_cancel(uint32_t id);

/**
 * @brief 更新定时器系统，处理到期的定时器任务
 * 
 * @param elapsed 经过的时间(毫秒)
 */
void timer_update(uint32_t elapsed);

/**
 * @brief 销毁定时器系统，释放所有资源
 */
void timer_system_destroy(void);

/**
 * @brief 获取定时器系统中的定时器数量
 * 
 * @return 定时器数量
 */
uint32_t timer_count(void);

#endif /* TIMER_H */