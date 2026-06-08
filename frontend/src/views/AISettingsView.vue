<template>
  <div>
    <div class="page-title">
      <h1>AI 设置</h1>
    </div>

    <section class="panel">
      <h2 class="section-title">通用 AI Provider</h2>
      <el-alert title="当前阶段保留 OpenAI-compatible Provider 配置界面，后端 AI 接口返回 Mock 结果。" type="info" :closable="false" />
      <el-form label-width="120px" class="settings-form">
        <el-form-item label="Provider">
          <el-input v-model="provider.name" />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="provider.baseUrl" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="provider.apiKey" type="password" show-password />
        </el-form-item>
        <el-form-item label="Model">
          <el-input v-model="provider.model" />
        </el-form-item>
        <el-form-item>
          <el-switch v-model="provider.enabled" active-text="启用" />
        </el-form-item>
        <el-button type="primary" @click="saveProvider">保存配置</el-button>
      </el-form>
    </section>

    <section class="panel rag-panel">
      <h2 class="section-title">RAG 问答配置</h2>
      <el-alert title="配置向量检索（Embedding）和对话生成（Chat）所用的 API，保存后立即生效。" type="info" :closable="false" style="margin-bottom: 16px" />

      <el-form label-width="140px" class="settings-form">
        <div class="config-group-title">Embedding（硅基流动）</div>
        <el-form-item label="API Key">
          <el-input v-model="rag.siliconflow_api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="rag.siliconflow_base_url" />
        </el-form-item>
        <el-form-item label="Embedding 模型">
          <el-input v-model="rag.embedding_model" />
        </el-form-item>

        <div class="config-group-title" style="margin-top: 20px">Chat 生成（DeepSeek）</div>
        <el-form-item label="API Key">
          <el-input v-model="rag.deepseek_api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="rag.deepseek_base_url" />
        </el-form-item>
        <el-form-item label="Chat 模型">
          <el-input v-model="rag.deepseek_model" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="saveRag">保存 RAG 配置</el-button>
        </el-form-item>
      </el-form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { rssApi, type RagConfig } from '../api/client'

const provider = reactive({
  name: 'OpenAI Compatible Demo',
  baseUrl: 'https://api.example.com/v1',
  apiKey: '',
  model: 'gpt-compatible-demo',
  enabled: true
})

const rag = reactive<RagConfig>({
  siliconflow_api_key: '',
  siliconflow_base_url: 'https://api.siliconflow.cn/v1',
  embedding_model: 'BAAI/bge-m3',
  deepseek_api_key: '',
  deepseek_base_url: 'https://api.deepseek.com',
  deepseek_model: 'deepseek-v4-flash',
})

const saving = ref(false)

onMounted(async () => {
  try {
    const cfg = await rssApi.getRagConfig()
    Object.assign(rag, cfg)
  } catch {
    // 后端未启动时忽略
  }
})

function saveProvider() {
  ElMessage.success('Provider 配置界面已预留，后续接入 llm_providers 表')
}

async function saveRag() {
  saving.value = true
  try {
    await rssApi.saveRagConfig({ ...rag })
    ElMessage.success('RAG 配置已保存')
  } catch {
    ElMessage.error('保存失败，请检查后端是否运行')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.settings-form {
  max-width: 720px;
  margin-top: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--el-text-color-primary);
}

.rag-panel {
  margin-top: 20px;
}

.config-group-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  margin-bottom: 12px;
  padding-left: 4px;
  border-left: 3px solid var(--el-color-primary);
  padding-left: 8px;
}
</style>
