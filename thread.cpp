#include <iostream>
#include <vector>
#include <queue>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <future>

class ThreadPool {
private:
    // 线程池
    std::vector<std::thread> workers;
    // 任务队列
    std::queue<std::function<void()>> tasks;
    
    // 同步相关
    std::mutex queue_mutex;
    std::condition_variable condition;
    bool stop;

public:
    // 构造函数，size为线程池大小
    ThreadPool(size_t size) : stop(false) {
        for(size_t i = 0; i < size; ++i) {
            workers.emplace_back([this] {
                while(true) {
                    std::function<void()> task;
                    
                    {
                        std::unique_lock<std::mutex> lock(this->queue_mutex);
                        
                        // 等待条件：直到stop为true或有任务
                        this->condition.wait(lock, [this] {
                            return this->stop || !this->tasks.empty();
                        });
                        
                        // 如果线程池停止且任务队列为空，退出线程
                        if(this->stop && this->tasks.empty()) {
                            return;
                        }
                        
                        // 获取任务
                        task = std::move(this->tasks.front());
                        this->tasks.pop();
                    }
                    
                    // 执行任务
                    task();
                }
            });
        }
    }
    
    // 添加任务到线程池
    template<class F>
    auto enqueue(F&& f) -> std::future<decltype(f())> {
        using return_type = decltype(f());
        
        // 创建一个packaged_task
        auto task = std::make_shared<std::packaged_task<return_type()>>(
            std::forward<F>(f)
        );
        
        std::future<return_type> res = task->get_future();
        {
            std::unique_lock<std::mutex> lock(queue_mutex);
            
            // 如果线程池已停止，抛出异常
            if(stop) {
                throw std::runtime_error("enqueue on stopped ThreadPool");
            }
            
            // 将任务添加到队列
            tasks.emplace([task]() { (*task)(); });
        }
        
        // 通知一个等待中的线程
        condition.notify_one();
        return res;
    }
    
    // 析构函数
    ~ThreadPool() {
        {
            std::unique_lock<std::mutex> lock(queue_mutex);
            stop = true;
        }
        
        // 通知所有线程
        condition.notify_all();
        
        // 等待所有线程完成
        for(std::thread &worker: workers) {
            worker.join();
        }
    }
};

// 使用示例
int main() {
    // 创建一个有4个线程的线程池
    ThreadPool pool(4);
    
    
    // 创建一些future来获取结果
    std::vector<std::future<int>> results;
    
    // 添加一些任务
    for(int i = 0; i < 8; ++i) {
        results.emplace_back(
            pool.enqueue([i] {
                std::cout << "task " << i << " is running in thread " 
                         << std::this_thread::get_id() << std::endl;
                std::this_thread::sleep_for(std::chrono::seconds(1));
                return i * i;
            })
        );
    }
    
    // 获取结果
    for(auto && result: results) {
        std::cout << "result: " << result.get() << std::endl;
    }
    
    return 0;
}
