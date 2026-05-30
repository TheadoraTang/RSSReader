<template>
  <div class="reader-grid" v-loading="store.loading">
    <section class="panel scroll-panel article-list-panel">
      <h2>订阅与筛选</h2>
      <el-button class="filter-button" text @click="loadArticles()">
        全部文章
      </el-button>
      <el-button class="filter-button" text @click="loadArticles({ unread: true })">
        未读文章
      </el-button>
      <el-button class="filter-button" text @click="loadArticles({ starred: true })">
        收藏文章
      </el-button>
      <el-divider />
      <h3>订阅源</h3>
      <el-button
        v-for="feed in store.feeds"
        :key="feed.id"
        class="filter-button"
        text
        @click="loadArticles({ feed_id: feed.id })"
      >
        {{ feed.title }}
      </el-button>
    </section>

    <section class="panel scroll-panel">
      <div class="toolbar">
        <template v-if="multiExportMode">
          <el-button text @click="exitMultiExportMode">取消</el-button>
          <span class="selection-status">{{ selectedBatchCount }} 已选择</span>
          <el-button type="primary" :disabled="selectedBatchCount === 0" @click="openBatchExportDialog">
            继续
          </el-button>
        </template>
        <template v-else>
          <div class="toolbar-actions">
            <el-button :icon="Refresh" @click="syncAll">同步全部</el-button>
            <el-button @click="beginMultiExportMode">批量导出</el-button>
          </div>
        </template>
      </div>

      <article
        v-for="article in store.articles"
        :key="article.id"
        class="article-item"
        :class="{
          active: !multiExportMode && store.selectedArticle?.id === article.id,
          selectable: multiExportMode,
          selected: multiExportMode && isArticleBatchSelected(article.id),
        }"
        @click="handleArticleClick(article.id)"
      >
        <div class="article-row">
          <el-checkbox
            v-if="multiExportMode"
            :model-value="isArticleBatchSelected(article.id)"
            @click.stop="toggleBatchSelection(article.id)"
          />
          <div class="article-meta">
            <h3>{{ article.title }}</h3>
            <p class="muted">{{ article.feed_title }}</p>
            <div class="article-tags">
              <el-tag v-if="!article.is_read" size="small">未读</el-tag>
              <el-tag v-if="article.is_starred" size="small" type="warning">收藏</el-tag>
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="panel scroll-panel" v-if="store.selectedArticle">
      <div class="toolbar">
        <el-button :icon="Check" :disabled="multiExportMode" @click="store.toggleRead(store.selectedArticle)">
          {{ store.selectedArticle.is_read ? "标记未读" : "标记已读" }}
        </el-button>
        <el-button :icon="Star" :disabled="multiExportMode" @click="store.toggleStar(store.selectedArticle)">
          {{ store.selectedArticle.is_starred ? "取消收藏" : "收藏" }}
        </el-button>
        <el-button :icon="MagicStick" :disabled="multiExportMode" @click="runSummary">
          生成摘要
        </el-button>
        <el-button :icon="Switch" :disabled="multiExportMode" @click="runTranslate">
          翻译
        </el-button>
      </div>
      <h1 class="reader-title">{{ store.selectedArticle.title }}</h1>
      <p class="muted">
        <span v-if="store.selectedArticle.author">{{ store.selectedArticle.author }} · </span>
        <a
          class="article-source-link"
          :href="store.selectedArticle.url"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ store.selectedArticle.url }}
        </a>
      </p>
      <div ref="articleBodyRef" class="article-body" v-html="store.selectedArticle.cleaned_html"></div>
      <el-alert
        v-if="aiResult"
        :title="aiResult"
        type="success"
        show-icon
        :closable="false"
      />
      <el-divider />
      <h2 class="reader-section-title">笔记</h2>
      <el-input
        v-model="note"
        type="textarea"
        :rows="6"
        placeholder="写下这篇文章的 Markdown 笔记"
        :disabled="multiExportMode"
      />
      <div class="note-actions">
        <el-button type="primary" :disabled="multiExportMode" @click="saveNote">保存笔记</el-button>
        <el-button :disabled="multiExportMode" :loading="exportingMarkdown" @click="exportMarkdown">
          {{ exportingMarkdown ? "正在导出..." : "导出 Markdown" }}
        </el-button>
      </div>
    </section>
  </div>

  <el-dialog v-model="batchDigestDialogVisible" title="批量导出文摘" width="720px">
    <div class="digest-dialog">
      <div class="digest-meta-grid">
        <div>
          <div class="digest-meta-label">选中文章</div>
          <div>{{ selectedBatchCount }}</div>
        </div>
        <div>
          <div class="digest-meta-label">Digest 标题</div>
          <div>{{ batchDigestPreview?.digest_title || "加载中" }}</div>
        </div>
        <div>
          <div class="digest-meta-label">导出文件名</div>
          <div>{{ batchDigestPreview?.filename || "加载中" }}</div>
        </div>
      </div>

      <div class="digest-options">
        <el-checkbox v-model="includeBatchSummary">包含 AI 摘要</el-checkbox>
        <el-checkbox v-model="includeBatchNote">包含笔记</el-checkbox>
      </div>

      <el-alert
        v-if="batchDigestPreview?.skipped_article_ids.length"
        type="warning"
        show-icon
        :closable="false"
        :title="`有 ${batchDigestPreview.skipped_article_ids.length} 篇文章因缺少标题或链接被跳过。`"
      />

      <div v-if="batchDigestLoading" class="digest-preview loading-state">
        正在生成预览...
      </div>
      <pre v-else class="digest-preview">{{ batchDigestPreview?.markdown || "" }}</pre>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="batchDigestDialogVisible = false">关闭</el-button>
        <el-button :disabled="!batchDigestPreview?.markdown" @click="copyBatchDigest">
          复制
        </el-button>
        <el-button
          type="primary"
          :disabled="!batchDigestPreview?.markdown"
          :loading="batchDigestExporting"
          @click="exportBatchDigest"
        >
          导出
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { Check, MagicStick, Refresh, Star, Switch } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import type { BatchDigestExportResponse } from "../api/client";
import { rssApi } from "../api/client";
import { useReaderStore } from "../stores/reader";

const store = useReaderStore();
const note = ref("");
const aiResult = ref("");
const articleBodyRef = ref<HTMLElement | null>(null);
const exportingMarkdown = ref(false);
const multiExportMode = ref(false);
const selectedBatchArticleIds = ref<number[]>([]);
const batchDigestDialogVisible = ref(false);
const includeBatchSummary = ref(false);
const includeBatchNote = ref(false);
const batchDigestLoading = ref(false);
const batchDigestExporting = ref(false);
const batchDigestPreview = ref<BatchDigestExportResponse | null>(null);
const isDesktop = Boolean(window.rssReaderDesktop?.saveMarkdown);

const orderedSelectedBatchIds = computed(() => {
  const selected = new Set(selectedBatchArticleIds.value);
  return store.articles.filter((article) => selected.has(article.id)).map((article) => article.id);
});

const selectedBatchCount = computed(() => orderedSelectedBatchIds.value.length);

onMounted(async () => {
  await store.loadAll();
  await loadNote();
});

watch(() => store.selectedArticle?.id, loadNote);
watch(() => store.selectedArticle?.cleaned_html, decorateArticleLinks, {
  flush: "post",
});
watch([batchDigestDialogVisible, includeBatchSummary, includeBatchNote], async ([visible]) => {
  if (visible) {
    await refreshBatchDigestPreview();
  }
});

async function loadArticles(params?: Record<string, unknown>) {
  exitMultiExportMode();
  store.articles = await rssApi.articles(params);
  store.selectedArticle = store.articles[0] ?? null;
}

async function loadNote() {
  if (!store.selectedArticle) return;
  const data = await rssApi.note(store.selectedArticle.id);
  note.value = data.content_markdown;
  aiResult.value = "";
}

async function decorateArticleLinks() {
  await nextTick();
  articleBodyRef.value?.querySelectorAll("a").forEach((link) => {
    link.setAttribute("target", "_blank");
    link.setAttribute("rel", "noopener noreferrer");
  });
}

async function saveNote() {
  if (!store.selectedArticle) return;
  await rssApi.saveNote(store.selectedArticle.id, note.value);
  ElMessage.success("笔记已保存");
}

async function exportMarkdown() {
  if (!store.selectedArticle) return;
  exportingMarkdown.value = true;
  try {
    const blob = await rssApi.exportArticleMarkdown(store.selectedArticle.id);
    triggerBrowserDownload(blob, `${safeFilename(store.selectedArticle.title)}.md`);
    ElMessage.success("Markdown 已导出");
  } catch (error) {
    ElMessage.error("导出失败，请确认后端已启动");
  } finally {
    exportingMarkdown.value = false;
  }
}

function beginMultiExportMode() {
  if (!store.articles.length) {
    ElMessage.warning("当前列表没有可导出的文章");
    return;
  }
  multiExportMode.value = true;
  selectedBatchArticleIds.value = [];
  batchDigestDialogVisible.value = false;
  batchDigestPreview.value = null;
}

function exitMultiExportMode() {
  multiExportMode.value = false;
  selectedBatchArticleIds.value = [];
  batchDigestDialogVisible.value = false;
  includeBatchSummary.value = false;
  includeBatchNote.value = false;
  batchDigestPreview.value = null;
}

function handleArticleClick(articleId: number) {
  if (multiExportMode.value) {
    toggleBatchSelection(articleId);
    return;
  }
  store.selectArticle(articleId);
}

function toggleBatchSelection(articleId: number) {
  if (isArticleBatchSelected(articleId)) {
    selectedBatchArticleIds.value = selectedBatchArticleIds.value.filter((id) => id !== articleId);
    return;
  }
  selectedBatchArticleIds.value = [...selectedBatchArticleIds.value, articleId];
}

function isArticleBatchSelected(articleId: number) {
  return selectedBatchArticleIds.value.includes(articleId);
}

function openBatchExportDialog() {
  if (!selectedBatchCount.value) {
    ElMessage.warning("请先选择至少一篇文章");
    return;
  }
  batchDigestDialogVisible.value = true;
}

async function refreshBatchDigestPreview() {
  if (!batchDigestDialogVisible.value || !orderedSelectedBatchIds.value.length) {
    return;
  }
  batchDigestLoading.value = true;
  try {
    batchDigestPreview.value = await rssApi.exportBatchDigestMarkdown({
      article_ids: orderedSelectedBatchIds.value,
      include_summary: includeBatchSummary.value,
      include_note: includeBatchNote.value,
    });
  } catch (error) {
    batchDigestPreview.value = null;
    batchDigestDialogVisible.value = false;
    ElMessage.error("批量导出预览生成失败");
  } finally {
    batchDigestLoading.value = false;
  }
}

async function copyBatchDigest() {
  const markdown = batchDigestPreview.value?.markdown;
  if (!markdown) return;
  await navigator.clipboard.writeText(markdown);
  ElMessage.success("Markdown 已复制");
}

async function exportBatchDigest() {
  const preview = batchDigestPreview.value;
  if (!preview?.markdown) return;
  batchDigestExporting.value = true;
  try {
    if (isDesktop && window.rssReaderDesktop?.saveMarkdown) {
      const result = await window.rssReaderDesktop.saveMarkdown({
        content: preview.markdown,
        suggestedFilename: preview.filename,
      });
      if (result.canceled) {
        return;
      }
      ElMessage.success(result.filePath ? `Markdown 已导出到 ${result.filePath}` : "Markdown 已导出");
    } else {
      triggerBrowserDownload(new Blob([preview.markdown], { type: "text/markdown;charset=utf-8" }), preview.filename);
      ElMessage.success("Markdown 已导出");
    }

    exitMultiExportMode();
  } catch (error) {
    ElMessage.error("批量导出失败");
  } finally {
    batchDigestExporting.value = false;
  }
}

function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function safeFilename(name: string) {
  return name.replace(/[\\/:*?"<>|]/g, "_").slice(0, 80) || "article";
}

async function runSummary() {
  if (!store.selectedArticle) return;
  const data = await rssApi.summary(store.selectedArticle.id);
  aiResult.value = data.result;
}

async function runTranslate() {
  if (!store.selectedArticle) return;
  const data = await rssApi.translate(store.selectedArticle.id);
  aiResult.value = data.result;
}

async function syncAll() {
  exitMultiExportMode();
  await rssApi.syncAll();
  ElMessage.success("Mock 同步已触发");
}
</script>

<style scoped>
.filter-button {
  width: 100%;
  justify-content: flex-start;
  margin: 2px 0;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.article-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.article-meta {
  flex: 1;
  min-width: 0;
}

.article-tags {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.selection-status {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.article-item.selectable {
  cursor: pointer;
}

.article-item.selected {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.digest-dialog {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.digest-meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.digest-meta-label {
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.digest-options {
  display: flex;
  gap: 16px;
}

.digest-preview {
  min-height: 260px;
  max-height: 420px;
  overflow: auto;
  margin: 0;
  padding: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid var(--el-border-color);
  border-radius: 10px;
  background: var(--el-fill-color-light);
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 13px;
  line-height: 1.6;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.tag-filter {
  margin: 4px;
  cursor: pointer;
}
</style>
