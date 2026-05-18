# Vue3 性能优化最佳实践

## 计算属性缓存
- 昂贵的计算逻辑必须放在 computed 中，不能放在 methods 或 template 表达式里
- computed 会缓存结果，只在依赖变化时重新计算
- methods 每次渲染都会重新执行，无缓存

错误示例：
<template>
  <p>{{item.filter(i => i.active).length}}</p> <!-- 每次渲染都计算 -->
</template>

正确示例：
const activeCount = computed(() => items.value.filter(i => i.active).length)

## v-if vs v-show
- v-if: 条件为 false 时元素不存在 DOM，适合切换频率低的场景
- v-show：条件为false 时元素仍存在DOM（display:none）,适合频繁切换的场景

## 大列表虚拟滚动
- 列表超过 100 条时应该使用虚拟滚动（vue-virtual-scrolle 或vueuse/useVirtualList）
- 虚拟滚动只渲染可视区域内的元素，避免大量DOM节点

## 异步组件懒加载
- 非首屏组件应使用defineAsyncComponent 懒加载
- 路由级别的懒加载用动态import()

正确示例：
const HeavyChart = defineAsyncComponent(() => import('./HeavyChart.vue'))

## watch 防抖
- watch 回调中有时耗时操作时，应加防抖避免频繁触发
- 使用 vueuse 的 watchDebounced 或手动加 debounce
