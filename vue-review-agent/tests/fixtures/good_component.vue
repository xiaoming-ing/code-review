<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface Props {
  userId: string
  userName: string
}

const props = defineProps<Props>()
const emit = defineEmits<{ update: [value: string] }>()

const DEBOUNCE_DELAY_MS = 300
const searchQuery = ref('')

const filteredName = computed(() => props.userName.trim().toLowerCase())

watch(searchQuery, (newVal) => {
  emit('update', newVal)
}, { debounce: DEBOUNCE_DELAY_MS })
</script>

<template>
  <div class="user-card">
    <p>{{ filteredName }}</p>
    <input v-model="searchQuery" placeholder="Search" />
  </div>
</template>

<style scoped>
.user-card { padding: 16px; }
</style>
