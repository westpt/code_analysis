/**
 * @file test_timer.c
 * @brief 定时器系统测试程序
 */

#include "include/timer.h"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h> // 用于sleep函数

// 定时器回调函数
void timer_callback(void* arg) {
    int* count = (int*)arg;
    printf("Timer triggered! Count: %d\n", *count);
    (*count)++;
}

int main() {
    printf("Timer System Test\n");
    
    // 初始化定时器系统
    if (!timer_system_init()) {
        printf("Failed to initialize timer system!\n");
        return 1;
    }
    
    // 创建计数器变量
    int count = 0;
    
    // 创建一个重复执行的定时器，每1000毫秒触发一次
    uint32_t timer_id = timer_create(1000, timer_callback, &count, true);
    if (timer_id == 0) {
        printf("Failed to create timer!\n");
        return 1;
    }
    
    printf("Created timer with ID: %u\n", timer_id);
    
    // 启动定时器
    if (!timer_start(timer_id)) {
        printf("Failed to start timer!\n");
        return 1;
    }
    
    printf("Timer started. Will update 5 times...\n");
    
    // 模拟时间流逝，更新定时器系统
    for (int i = 0; i < 5; i++) {
        printf("Updating timer system...\n");
        timer_update(1000); // 更新1000毫秒
        usleep(100000);     // 实际等待100毫秒，只是为了看到输出
    }
    
    // 暂停定时器
    printf("Pausing timer...\n");
    if (!timer_pause(timer_id)) {
        printf("Failed to pause timer!\n");
    }
    
    // 再次更新，由于定时器已暂停，不应触发回调
    printf("Updating timer system while paused...\n");
    timer_update(1000);
    
    // 取消定时器
    printf("Cancelling timer...\n");
    if (!timer_cancel(timer_id)) {
        printf("Failed to cancel timer!\n");
    }
    
    // 获取定时器数量
    printf("Timer count: %u\n", timer_count());
    
    // 销毁定时器系统
    printf("Destroying timer system...\n");
    timer_system_destroy();
    
    printf("Test completed.\n");
    return 0;
}