<template>
  <el-container class="app-shell">
    <el-header class="top-nav">
      <div class="brand" style="display: flex; align-items: center; gap: 4px">
        <strong>RSSReader</strong>
        <span>Local-first</span>
      </div>
      <div class="top-actions">
        <el-tooltip content="AI 设置" placement="bottom">
          <el-button
            :icon="MagicStick"
            text
            circle
            aria-label="AI 设置"
            @click="router.push('/ai')"
          />
        </el-tooltip>
        <el-tooltip content="设置" placement="bottom">
          <el-button
            :icon="Setting"
            text
            circle
            aria-label="设置"
            @click="router.push('/settings')"
          />
        </el-tooltip>
      </div>
    </el-header>
    <el-container class="content-shell">
      <el-aside class="nav" width="64px">
        <el-menu router :default-active="$route.path" class="nav-menu">
          <el-menu-item index="/" title="阅读">
            <el-icon><Reading /></el-icon>
            <span>阅读</span>
          </el-menu-item>
          <el-menu-item index="/feeds" title="订阅">
            <el-icon><Connection /></el-icon>
            <span>订阅</span>
          </el-menu-item>
          <el-menu-item index="/stats" title="统计日志">
            <el-icon><DataAnalysis /></el-icon>
            <span>统计日志</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import {
  Connection,
  DataAnalysis,
  MagicStick,
  Reading,
  Setting,
} from "@element-plus/icons-vue";
import { useRouter } from "vue-router";

const router = useRouter();
</script>
