# Vue 3 组件设计最佳实践

## Props 定义规范
- Props 必须声明类型，避免运行时错误
- 使用TypeScript 时优先用 defineProps<T>()泛型语法
- 非必填 props 应提供默认值

错误示例：
    props: ['id','name'] // 无类型声明

正确示例：
    const props = defineProps<{
        id: string
        name: string
        count?: number // 可选prop
    }>

## defineEmits 规范
- Vue 3要求显示声明所有 emit 事件
- 事件名使用kebad-case (如update-value而不是updateValue)
- 使用TypeScript 时声明参数类型

正确示例：
    const emit = defineEmits<{
        'update-value':[value: string]
        'item-click':[id:number,event:MouseEvent]
    }>()

## 组件命名规范
- 组件名必须是PascaCase(如UserCard、BaseButton)
- 必须是多词组合，避免与HTML原生元素冲突(不能叫Card,Button)
- 文件名与组件名保持一致

## script setup 最佳实践
- Vue3 推荐使用 <script setup>语法，更简洁且有更好的TypeScript 支持
- 不要混用 <script> 和 <script setup>
- 文件结构顺序： <script setup> → <template> → <style scoped>

## v-model 使用规范
- 父组件传递v-model 给子组件时，子组件用defineModel()接收
- 自定义 v-model 修饰符通过defineModel的第二个参数处理
