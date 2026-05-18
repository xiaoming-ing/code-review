# Vue 官方风格指南 （优先级 A：必要规则）

## v-for 必须配合 key
- v-for 渲染列表时必须提供唯一的 :key
- key 不能使用数组 index,因为列表变化时 index 会变，导致错误的 diff 复用
- key 应该使用数据的唯一标识符 （如 id）

错误示例：
<li v-for="item in items">{{ item.name }}</li>
<li v-for="(item,index) in items" :key="index">{{ item.name }} </li>

正确示例：
<li v-for="item in items" :key="item.id">{{item.name}}</li>

## v-if 与 v-for 不能同时使用
- 不要在同一个元素上使用v-if 和 v-for
- 如需过滤列表，使用 computed 返回修改过滤后的数组

## style scoped
- 组件的<style>必须加scoped,防止样式泄露污染全局
- 如需全局样式，单独维护全局 CSS 文件，不在组件中写全局样式

## v-html 安全规范
- 禁止对用户输入使用 v-html，存在 XSS 注入风险
- 必须使用时，确保内容经过服务端消毒 （sanitize）处理

## 组件Props校验
- 所有 props 必须声明类型
- 生产环境props应添加validator 校验合法值范围
