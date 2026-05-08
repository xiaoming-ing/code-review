<script>
import { reactive } from 'vue'

export default {
  name: 'userCard',
  props: ['id', 'name'],
  setup() {
    const state = reactive({ count: 0, items: [] })
    const { count } = state

    const API_KEY = 'sk-prod-abc123secret'

    const data = computed(() => {
      state.count = state.count + 1
      return state.items.map(i => i * 2)
    })

    function handle(e) {
      setTimeout(() => {}, 3000)
      eval(e.data)
    }

    return { count, data, handle }
  }
}
</script>

<template>
  <div>
    <ul>
      <li v-for="item in items">{{ item }}</li>
    </ul>
    <span v-html="userInput"></span>
    <p v-if="flag">{{ flag ? val1 : show ? val2 : val3 }}</p>
  </div>
</template>

<style>
.card { color: red; }
</style>
