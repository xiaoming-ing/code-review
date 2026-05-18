# Vue 3 响应式系统最佳实践

## ref vs reactive 选择原则
- 基础类型（string、number、boolean）必须用 ref()，不能用 reactive()
- 对象类型优先用 reactive()，但解构时会丢失响应式
- 解构 reactive 对象会导致响应式追踪丢失，必须用 toRefs() 或 toRef()

错误示例：
  const state = reactive({ count: 0 })
  const { count } = state  // count 丢失响应式，修改不触发更新

正确示例：
    const state = reactive({count:0})
    const { count } = toRefs(state) // count 保持响应式

## computed 使用规范
- computed 必须是纯函数，只能读取响应式数据，不能修改
- 在computed 内修改外部状态是副作用，会导致无限循环或不可预期行为
- 需要在数据变化时执行副作用，应使用 watch 或 watchEffect

错误示例：
    const doubled = computed(()=>{
        count.value++ // 错误：computed 内修改状态
        return count.value * 2
    })


## watch 使用规范
- watch 的第一个参数必须是响应式引用或getter函数
- 监听 reactive 对象的属性需要用 getter: () => state.count
- deep监听整个对象用 {deep:true},但有性能开销

## defineModel (Vue 3.4+)
- 子组件实现双向绑定应使用 defineModel() 而不是props+emit 组合
- defineModel 自动创建一个ref,同时声明prop何对应的update emit

正确示例：
const model = defineModel() // 等价于props.modelValue + emit('update:modelValue')
