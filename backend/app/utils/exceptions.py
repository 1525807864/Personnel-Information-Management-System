"""自定义业务异常"""
class BusinessException(Exception):
    def __init__(self,message:str,code:int=400):
        self.message = message
        self.code = code
        super().__init__(message)


class DuplicateDataException(BusinessException):
    """数据重复异常（409）"""
    def __init__(self,message:str="数据已存在"):
        super().__init__(message,code=409)
class UnauthorizedException(BusinessException):
    """未授权异常 (401)"""
    def __init__(self, message: str = "未授权访问"):
        super().__init__(message, code=401)


class NotFoundException(BusinessException):
    """资源不存在异常 (404)"""
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, code=404)


class ValidationException(BusinessException):
    """数据校验异常 (422)"""
    def __init__(self, message: str = "数据校验失败"):
        super().__init__(message, code=422)


class FileImportException(BusinessException):
    """文件导入异常"""
    def __init__(self, message: str = "文件导入失败"):
        super().__init__(message, code=400)


class AccountLockedException(BusinessException):
    """账户锁定异常 (423)"""
    def __init__(self, message: str = "账户已被锁定，请30分钟后重试"):
        super().__init__(message, code=423)