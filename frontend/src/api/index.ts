/**
 * API 统一导出
 * 使用带认证的 request 实例
 */

import request, { rawRequest } from './request'
export { tokenManager } from './token'

export default request
export { rawRequest }
