from .sdz import SDZExtension

def createPlugin(app):
    return SDZExtension(app)