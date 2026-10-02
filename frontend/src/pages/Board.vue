<template>
  <div>
    <h1 class="brand">本周看板</h1>
    <p class="muted">周卡片网格 · round-robin 落位后可去「对调」申请交换</p>
    <div class="topbar">
      <span class="chip" :class="{ coral: week && week.status === 'ready' }">
        {{ week && week.status === 'draft' ? '草稿' : '已生成' }}
      </span>
      <div v-if="latest" class="regen-pin">
        <div class="regen-pin-head">钉 · 最近重生成 #{{ latest.id }} · {{ latest.created_at }}</div>
        <div>{{ latest.reason }}</div>
      </div>
    </div>
    <div style="display:flex;gap:8px;margin:12px 0">
      <button @click="generate">生成周表</button>
      <button v-if="showForce" class="force-btn" @click="forceGenerate">强制重生成</button>
      <button class="ghost" @click="load">刷新</button>
    </div>
    <p v-if="err" class="err">{{ err }}</p>
    <section class="regen-section">
      <h2 class="brand regen-title">重生成履历</h2>
      <ul v-if="regenRows.length" class="list regen-list">
        <li v-for="(r, i) in regenRows" :key="r.id" :class="{ pinned: i === 0 }">
          <span class="pin-mark">钉 #{{ r.id }}</span>
          <span class="muted">{{ r.created_at }}</span>
          <div class="regen-reason">{{ r.reason }}</div>
        </li>
      </ul>
      <p v-else class="muted">暂无重生成履历</p>
    </section>
    <div class="week-grid">
      <article v-for="d in days" :key="d" class="week-card">
        <header>Day {{ d }}</header>
        <div v-for="a in byDay(d)" :key="a.id">
          <span class="chip">{{ a.task_title }}</span>
          <span class="chip coral">{{ a.member_name }}</span>
        </div>
        <p v-if="!byDay(d).length" class="muted">空</p>
      </article>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const assigns = ref([])
const week = ref(null)
const latest = ref(null)
const regenRows = ref([])
const showForce = ref(false)
const days = [0,1,2,3,4,5,6]
const err = ref('')
const weekId = 1
function byDay(d) { return assigns.value.filter(a => a.day === d) }
async function load() {
  err.value = ''
  try {
    const b = await api('/weeks/' + weekId + '/board')
    assigns.value = b.assignments || []
    week.value = b.week || null
    latest.value = b.latest_regen || null
  } catch (e) { err.value = e.message }
  try {
    regenRows.value = await api('/weeks/' + weekId + '/regenerations')
  } catch (e) { regenRows.value = [] }
}
async function generate() {
  err.value = ''
  showForce.value = false
  try {
    await api('/weeks/' + weekId + '/generate', { method: 'POST', body: '{}' })
    await load()
  } catch (e) {
    if (e.message === 'ready_requires_force') {
      err.value = '周表已生成且已有排班格，普通重生成已锁定，格表未改动。如需覆盖，请填写理由后强制重生成。'
      showForce.value = true
    } else { err.value = e.message }
  }
}
async function forceGenerate() {
  err.value = ''
  const input = window.prompt('请输入强制重生成理由（不能为空）')
  if (input === null) return
  const reason = input.trim()
  if (!reason) { err.value = '理由不能为空' ; return }
  try {
    await api('/weeks/' + weekId + '/generate', {
      method: 'POST', body: JSON.stringify({ force: true, reason }),
    })
    showForce.value = false
    await load()
  } catch (e) {
    err.value = e.message === 'force_requires_reason' ? '理由不能为空' : e.message
  }
}
onMounted(load)
</script>
