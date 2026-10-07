---
name: "source-command-optimize"
description: "分析代码中的性能问题并提出优化建议"
---

# source-command-optimize

Use this skill when the user asks to run the migrated source command `optimize`.

## Command Template

# Code Optimization / 代码优化

请按优先级检查代码中的这些问题：

1. **Performance bottlenecks**：是否存在 O(n²) 操作、低效循环、重复查询
2. **Memory leaks**：是否有资源未释放、缓存失控、循环引用等问题
3. **Algorithm improvements**：是否有更合适的数据结构或算法
4. **Caching opportunities**：哪些重复计算或查询适合缓存
5. **Concurrency issues**：是否存在竞态条件、锁问题、线程安全隐患

输出格式请包含：

- 问题严重级别：Critical / High / Medium / Low
- 位置
- 原因解释
- 推荐修复方式
- 必要时给出代码示例
