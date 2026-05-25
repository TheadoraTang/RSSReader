<template>
  <div>
    <div class="page-title">
      <h1>设置</h1>
    </div>
    <section class="panel">
      <el-form label-width="120px">
        <el-form-item label="阅读字号">
          <el-slider v-model="fontSize" :min="14" :max="24" show-input />
        </el-form-item>
        <el-form-item label="阅读模式">
          <el-segmented v-model="readerTheme" :options="themeOptions" />
        </el-form-item>
      </el-form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ReaderTheme, usePreferencesStore } from '../stores/preferences'

const preferences = usePreferencesStore()
const themeOptions = [
  { label: '白天', value: 'light' },
  { label: '黑夜', value: 'dark' }
]

const fontSize = computed({
  get: () => preferences.readerFontSize,
  set: (value: number) => preferences.setReaderFontSize(value)
})

const readerTheme = computed({
  get: () => preferences.readerTheme,
  set: (value: ReaderTheme) => preferences.setReaderTheme(value)
})
</script>

