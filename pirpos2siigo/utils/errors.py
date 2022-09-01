# library errors
class ErrorSiigoToken(Exception):
    pass


class ErrorPirposToken(Exception):
    pass


class ErrorLoadingPirposClients(Exception):
    pass


class ErrorLoadingSiigoClients(Exception):
    pass


class ErrorLoadingPirposProducts(Exception):
    pass


class ErrorLoadingSiigoProducts(Exception):
    pass


class ErrorLoadingPirposInvoices(Exception):
    pass


class ErrorParsingPirposInvoices(Exception):
    pass
class ErrorCreatingCustomer(Exception):
    pass