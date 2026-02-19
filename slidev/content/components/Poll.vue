<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import { onWsMessage, sendWsMessage } from "../setup/main";

interface PollOption {
  id: string;
  label: string;
}

const props = withDefaults(
  defineProps<{
    pollId: string;
    question: string;
    options: PollOption[];
    maxChoices?: number;
  }>(),
  { maxChoices: 1 },
);

const selected = ref<Set<string>>(new Set());
const votes = ref<Record<string, number>>({});

const remainingChoices = computed(
  () => props.maxChoices - selected.value.size,
);

const totalVotes = computed(() =>
  Object.values(votes.value).reduce((sum, v) => sum + v, 0),
);

function selectOption(id: string) {
  if (selected.value.has(id)) return;
  if (remainingChoices.value <= 0) return;

  selected.value = new Set([...selected.value, id]);
  sendWsMessage({
    type: "poll_vote",
    pollId: props.pollId,
    choice: id,
    options: props.options.map((o) => o.id),
    maxChoices: props.maxChoices,
  });
}

let unsubscribe: (() => void) | null = null;

onMounted(() => {
  unsubscribe = onWsMessage((data) => {
    if (data.type === "poll_state" && data.pollId === props.pollId) {
      votes.value = (data.votes as Record<string, number>) || {};
    }
  });
});

onUnmounted(() => {
  unsubscribe?.();
});
</script>

<template>
  <div class="poll-container">
    <h3 class="poll-question">{{ question }}</h3>
    <p v-if="maxChoices > 1" class="poll-hint">
      最大{{ maxChoices }}つ選択できます（残り{{ remainingChoices }}）
    </p>

    <div class="poll-options">
      <button
        v-for="opt in options"
        :key="opt.id"
        class="poll-option"
        :class="{
          selected: selected.has(opt.id),
          disabled: selected.has(opt.id) || remainingChoices <= 0,
        }"
        @click="selectOption(opt.id)"
      >
        <span class="poll-check">{{ selected.has(opt.id) ? "✓" : "" }}</span>
        <span class="poll-label">{{ opt.label }}</span>
        <span v-if="votes[opt.id] != null" class="poll-count">
          {{ votes[opt.id] }}票
        </span>
      </button>
    </div>

    <div v-if="totalVotes > 0" class="poll-results">
      <div v-for="opt in options" :key="opt.id" class="poll-bar-row">
        <span class="poll-bar-label">{{ opt.label }}</span>
        <div class="poll-bar-track">
          <div
            class="poll-bar-fill"
            :style="{
              width: `${((votes[opt.id] || 0) / totalVotes) * 100}%`,
            }"
          />
        </div>
        <span class="poll-bar-value">{{ votes[opt.id] || 0 }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.poll-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem;
}

.poll-question {
  font-size: 1.6rem;
  color: #4ec9b0;
  margin: 0;
}

.poll-hint {
  font-size: 0.9rem;
  color: #aaa;
  margin: 0;
}

.poll-options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
  max-width: 500px;
}

.poll-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border: 2px solid #555;
  border-radius: 8px;
  background: transparent;
  color: #eee;
  font-size: 1.1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.poll-option:hover:not(.disabled) {
  border-color: #4ec9b0;
}

.poll-option.selected {
  border-color: #4ec9b0;
  background: rgba(78, 201, 176, 0.15);
}

.poll-option.disabled {
  cursor: default;
  opacity: 0.8;
}

.poll-check {
  width: 1.2rem;
  text-align: center;
  color: #4ec9b0;
  font-weight: bold;
}

.poll-label {
  flex: 1;
  text-align: left;
}

.poll-count {
  color: #aaa;
  font-size: 0.9rem;
}

.poll-results {
  width: 100%;
  max-width: 500px;
}

.poll-bar-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}

.poll-bar-label {
  width: 140px;
  text-align: right;
  font-size: 0.9rem;
  color: #ccc;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.poll-bar-track {
  flex: 1;
  height: 20px;
  background: #333;
  border-radius: 4px;
  overflow: hidden;
}

.poll-bar-fill {
  height: 100%;
  background: #4ec9b0;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.poll-bar-value {
  width: 2.5rem;
  text-align: right;
  font-size: 0.9rem;
  color: #aaa;
}
</style>
