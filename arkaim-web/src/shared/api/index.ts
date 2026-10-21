/**
 * shared/api — typed contract layer (баррел).
 * Единственная дверь к сети для всего приложения (красная линия F1).
 */

export { apiCall, setBearer, type RequestOptions } from './client';
export { ApiError, parseErrorBody, type ApiErrorCode } from './errors';
export { ENVELOPE_MAP, envelopeOf } from './envelope';
export * from './contracts/auth';
export * from './contracts/book';
export * from './contracts/reader';
export * from './contracts/temporal';
export * from './contracts/world';
export * from './contracts/worldExplorer';
export * from './contracts/knowledge';
export * from './contracts/studio';
export * from './contracts/community';
export * from './contracts/presence';
export * from './contracts/email';
export * from './contracts/drafts';
