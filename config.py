class Config:
    SECRET_KEY = "dev-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///fxport.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = "jwt-secret"
    PAYSTACK_SECRET_KEY="sk_test_115cae373be5512695afb76982585a5f03971af6"