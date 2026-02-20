import { addSyncMethod } from "@slidev/client";
import { defineAppSetup } from "@slidev/types";
import {
	ConnectionStatusEnum,
	changeConnectionState,
	connectionStatus,
	getWsInstance,
	setWsInstance,
} from "./connectionState";

// ロール判定はサーバー側でCookieベースで行う
const SYNC_SERVER = `${window.location.origin.replace(/^http/, "ws")}/ws`;

let reconnectTimer: number | null = null;

type MessageHandler = (data: Record<string, unknown>) => void;
const messageHandlers: MessageHandler[] = [];

export function onWsMessage(handler: MessageHandler) {
	messageHandlers.push(handler);
	return () => {
		const idx = messageHandlers.indexOf(handler);
		if (idx >= 0) messageHandlers.splice(idx, 1);
	};
}

export function sendWsMessage(data: Record<string, unknown>): boolean {
	const ws = getWsInstance();
	if (ws?.readyState === WebSocket.OPEN) {
		ws.send(JSON.stringify(data));
		return true;
	}
	return false;
}

let connected = false;

export function connectWebSocket(onUpdate: (data: Partial<object>) => void): void {
	if (connected) return;
	connected = true;

	// 既存のタイマーをクリア
	if (reconnectTimer) {
		clearTimeout(reconnectTimer);
		reconnectTimer = null;
	}

	const ws = new WebSocket(SYNC_SERVER);
	setWsInstance(ws);

	ws.onopen = () => {
		changeConnectionState(ConnectionStatusEnum.Connected);
	};

	ws.onmessage = (event) => {
		try {
			if (connectionStatus.value === ConnectionStatusEnum.Connected) {
				const data = JSON.parse(event.data);
				// Dispatch to registered handlers
				for (const handler of messageHandlers) {
					handler(data);
				}
				// Messages without "type" field go to slide sync (backward compat)
				if (!data.type) {
					onUpdate(data);
				}
			}
		} catch (e) {
			console.error("Failed to parse sync message", e);
		}
	};

	ws.onclose = () => {
		connected = false;
		// Disconnected状態の場合は自動再接続しない
		if (connectionStatus.value === ConnectionStatusEnum.Disconnected) {
			return;
		}

		changeConnectionState(ConnectionStatusEnum.Connecting);
		reconnectTimer = setTimeout(() => {
			reconnectTimer = null;
			connectWebSocket(onUpdate);
		}, 3000) as unknown as number;
	};
}

interface Sync {
	init: <State extends object>(
		channelKey: string,
		onUpdate: (data: Partial<State>) => void,
		state: State,
		persist?: boolean,
	) => ((state: State, updating?: boolean) => void) | undefined;
}

const websocketSync: Sync = {
	init(_channelKey, onUpdate, _state, persist) {
		if (persist) return undefined;

		connectWebSocket(onUpdate);

		return (state, updating) => {
            const ws = getWsInstance();
            if (!updating && ws?.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(state));
            }
		};
	},
};

export default defineAppSetup(({ app }) => {
	addSyncMethod(websocketSync);
});
