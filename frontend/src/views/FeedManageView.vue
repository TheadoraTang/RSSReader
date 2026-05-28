<template>
  <div>
    <div class="page-title">
      <h1>订阅管理</h1>
      <div class="toolbar">
        <el-button
          :icon="Refresh"
          :loading="syncingAll"
          :disabled="syncingAll || syncingFeedId !== null"
          @click="syncAll"
        >
          {{ syncingAll ? "正在同步..." : "同步全部" }}
        </el-button>
        <el-button :icon="Upload">OPML 导入</el-button>
        <el-button
          tag="a"
          href="/api/opml/export"
          target="_blank"
          :icon="Download"
          >OPML 导出</el-button
        >
      </div>
    </div>
    <section class="panel">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="title" placeholder="可选" />
        </el-form-item>
        <el-form-item label="RSS URL">
          <el-input
            v-model="url"
            placeholder="https://example.com/feed.xml"
            class="url-input"
          />
        </el-form-item>
        <el-button
          style="margin-left: 8px; margin-bottom: 18px"
          type="primary"
          :loading="addingFeed"
          :disabled="addingFeed || !url"
          @click="addFeed"
        >
          {{ addingFeed ? "正在添加..." : "添加订阅" }}
        </el-button>
      </el-form>
      <el-table :data="feeds" stripe>
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="url" label="URL" />
        <el-table-column label="最后同步" width="180">
          <template #default="{ row }">
            {{ formatLastSyncAt(row.last_sync_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button
              size="small"
              :loading="syncingFeedId === row.id"
              :disabled="isBusy"
              @click="syncFeed(row.id)"
            >
              {{ syncingFeedId === row.id ? "正在同步..." : "同步" }}
            </el-button>
            <el-popconfirm
              title="确定删除当前订阅吗？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              confirm-button-type="danger"
              @confirm="deleteFeed(row.id)"
            >
              <template #reference>
                <el-button
                  size="small"
                  type="danger"
                  plain
                  :loading="deletingFeedId === row.id"
                  :disabled="isBusy"
                >
                  删除
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Delete, Download, Refresh, Upload } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { Feed, rssApi } from "../api/client";

const feeds = ref<Feed[]>([]);
const title = ref("");
const url = ref("");
const addingFeed = ref(false);
const syncingAll = ref(false);
const syncingFeedId = ref<number | null>(null);
const deletingFeedId = ref<number | null>(null);
const isBusy = computed(
  () =>
    syncingAll.value ||
    syncingFeedId.value !== null ||
    deletingFeedId.value !== null,
);

onMounted(loadFeeds);

async function loadFeeds() {
  feeds.value = await rssApi.feeds();
}

function formatLastSyncAt(value?: string) {
  if (!value) return "未同步";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    hourCycle: "h23",
  }).formatToParts(date);
  const partMap = Object.fromEntries(
    parts.map((part) => [part.type, part.value]),
  );

  return `${partMap.year}/${partMap.month}/${partMap.day} ${partMap.hour}:${partMap.minute}:${partMap.second}`;
}

async function addFeed() {
  if (!url.value) return;
  addingFeed.value = true;
  try {
    await rssApi.createFeed({ title: title.value, url: url.value });
    title.value = "";
    url.value = "";
    await loadFeeds();
    ElMessage.success("订阅已添加");
  } catch (error) {
    ElMessage.error("添加订阅失败，请检查 RSS URL 或后端状态");
  } finally {
    addingFeed.value = false;
  }
}

async function syncFeed(id: number) {
  syncingFeedId.value = id;
  try {
    await rssApi.syncFeed(id);
    await loadFeeds();
    ElMessage.success("同步完成");
  } catch (error) {
    ElMessage.error("同步失败，请稍后重试");
  } finally {
    syncingFeedId.value = null;
  }
}

async function deleteFeed(id: number) {
  deletingFeedId.value = id;
  try {
    await rssApi.deleteFeed(id);
    await loadFeeds();
    ElMessage.success("订阅已删除");
  } catch (error) {
    ElMessage.error("删除订阅失败，请稍后重试");
  } finally {
    deletingFeedId.value = null;
  }
}

async function syncAll() {
  syncingAll.value = true;
  try {
    await rssApi.syncAll();
    await loadFeeds();
    ElMessage.success("全部订阅同步完成");
  } catch (error) {
    ElMessage.error("同步全部失败，请稍后重试");
  } finally {
    syncingAll.value = false;
  }
}
</script>

<style scoped>
.url-input {
  width: 360px;
}
</style>
