import type { EvaluationResponse } from "@/lib/evaluation-api";

const DATABASE_NAME = "upsc-copy-checker";
const STORE_NAME = "workflow";
const PENDING_KEY = "pending-submission";
const RESULT_KEY = "latest-result";
const NOTICE_KEY = "evaluation-home-notice";
let currentHomeNotice: string | null = null;
const noticeSubscribers = new Set<() => void>();

export interface PendingSubmission {
  answerCopy: File;
  referenceFiles: File[];
  questionText: string;
}

export interface StoredEvaluation {
  answerCopy: File;
  response: EvaluationResponse;
}

interface RecordValue<T> {
  key: string;
  value: T;
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, 1);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE_NAME)) {
        request.result.createObjectStore(STORE_NAME, { keyPath: "key" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Could not open local file storage."));
  });
}

async function writeRecord<T>(key: string, value: T): Promise<void> {
  const database = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).put({ key, value } satisfies RecordValue<T>);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error ?? new Error("Could not save evaluation data."));
    transaction.onabort = () => reject(transaction.error ?? new Error("Saving evaluation data was interrupted."));
  }).finally(() => database.close());
}

async function readRecord<T>(key: string): Promise<T | null> {
  const database = await openDatabase();
  return new Promise<T | null>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readonly");
    const request = transaction.objectStore(STORE_NAME).get(key);
    request.onsuccess = () => resolve((request.result as RecordValue<T> | undefined)?.value ?? null);
    request.onerror = () => reject(request.error ?? new Error("Could not read evaluation data."));
    transaction.oncomplete = () => database.close();
    transaction.onerror = () => {
      database.close();
      reject(transaction.error ?? new Error("Could not read evaluation data."));
    };
  });
}

async function deleteRecord(key: string): Promise<void> {
  const database = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).delete(key);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error ?? new Error("Could not clear temporary submission data."));
  }).finally(() => database.close());
}

export const savePendingSubmission = (submission: PendingSubmission) =>
  writeRecord(PENDING_KEY, submission);
export const getPendingSubmission = () => readRecord<PendingSubmission>(PENDING_KEY);
export const clearPendingSubmission = () => deleteRecord(PENDING_KEY);
export const saveLatestEvaluation = (result: StoredEvaluation) =>
  writeRecord(RESULT_KEY, result);
export const getLatestEvaluation = () => readRecord<StoredEvaluation>(RESULT_KEY);

export function setEvaluationHomeNotice(message: string): void {
  try {
    window.sessionStorage.setItem(NOTICE_KEY, message);
  } catch {
    // Keep the notice in memory for the current client-side navigation.
  }
  currentHomeNotice = message;
  noticeSubscribers.forEach((subscriber) => subscriber());
}

export function getEvaluationHomeNotice(): string | null {
  if (currentHomeNotice !== null) return currentHomeNotice;
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(NOTICE_KEY);
  } catch {
    return null;
  }
}

export function takeEvaluationHomeNotice(): string | null {
  let message = currentHomeNotice;
  try {
    message = message ?? window.sessionStorage.getItem(NOTICE_KEY);
    window.sessionStorage.removeItem(NOTICE_KEY);
  } catch {
    // The in-memory value is still cleared below.
  }
  currentHomeNotice = null;
  noticeSubscribers.forEach((subscriber) => subscriber());
  return message;
}

export function subscribeToEvaluationHomeNotice(
  callback: () => void,
): () => void {
  noticeSubscribers.add(callback);
  return () => noticeSubscribers.delete(callback);
}
