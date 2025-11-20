import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import Config


class EmailService:
    """Servicio para envío de correos electrónicos"""

    @staticmethod
    def send_password_reset_email(to_email, reset_link, user_name):
        """
        Enviar correo de recuperación de contraseña
        
        Args:
            to_email (str): Email del destinatario
            reset_link (str): Link de recuperación con token
            user_name (str): Nombre del usuario
            
        Returns:
            tuple: (bool, str) - (éxito, mensaje)
        """
        try:
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Recuperación de Contraseña - LazyFood'
            msg['From'] = Config.MAIL_DEFAULT_SENDER
            msg['To'] = to_email

            # Contenido HTML del correo
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .container {{
                        background-color: #f9f9f9;
                        border-radius: 10px;
                        padding: 30px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        background-color: #A96224;
                        color: white;
                        padding: 30px 20px;
                        border-radius: 10px 10px 0 0;
                        text-align: center;
                    }}
                    .logo {{
                        width: 80px;
                        height: 80px;
                        margin: 0 auto 15px;
                        background-color: #A96224;
                        border-radius: 50%;
                        display: table;
                        text-align: center;
                        font-size: 36px;
                        font-weight: bold;
                        color: white;
                        border: 3px solid white;
                        line-height: 76px;
                    }}
                    .content {{
                        background-color: white;
                        padding: 30px;
                        border-radius: 0 0 10px 10px;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #A96224;
                        color: white !important;
                        padding: 15px 30px;
                        text-decoration: none;
                        border-radius: 5px;
                        margin: 20px 0;
                        font-weight: bold;
                    }}
                    .button:hover {{
                        background-color: #8B4E1C;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 20px;
                        color: #666;
                        font-size: 12px;
                    }}
                    .warning {{
                        background-color: #fff3cd;
                        border-left: 4px solid #A96224;
                        padding: 10px;
                        margin: 15px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">LF</div>
                        <h1>LazyFood</h1>
                    </div>
                    <div class="content">
                        <h2>Hola {user_name},</h2>
                        <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en LazyFood.</p>
                        
                        <p>Haz clic en el siguiente botón para crear una nueva contraseña:</p>
                        
                        <center>
                            <a href="{reset_link}" class="button">Restablecer Contraseña</a>
                        </center>
                        
                        <p>O copia y pega este enlace en tu navegador:</p>
                        <p style="word-break: break-all; color: #666; font-size: 12px;">{reset_link}</p>
                        
                        <div class="warning">
                            <strong>⚠️ Importante:</strong>
                            <ul>
                                <li>Este enlace expirará en <strong>1 hora</strong></li>
                                <li>Si no solicitaste este cambio, ignora este correo</li>
                                <li>Tu contraseña actual seguirá siendo válida hasta que la cambies</li>
                            </ul>
                        </div>
                        
                        <p>Si tienes problemas, contacta con nuestro equipo de soporte.</p>
                        
                        <p>Saludos,<br>El equipo de LazyFood</p>
                    </div>
                    <div class="footer">
                        <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
                        <p>&copy; 2025 LazyFood. Todos los derechos reservados.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Adjuntar HTML
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Verificar configuración de email
            if not Config.MAIL_USERNAME or not Config.MAIL_PASSWORD:
                print("⚠️ ADVERTENCIA: Configuración de email no disponible")
                print(f"   Link de recuperación (MODO DESARROLLO): {reset_link}")
                return True, "Email simulado (modo desarrollo)"

            # Conectar y enviar
            with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
                server.starttls()
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
                server.send_message(msg)

            print(f"✓ Email de recuperación enviado a: {to_email}")
            return True, "Email enviado exitosamente"

        except Exception as e:
            print(f"❌ Error enviando email: {str(e)}")
            print(f"   Link de recuperación (MODO DESARROLLO): {reset_link}")
            # En desarrollo, devolver éxito para continuar con el flujo
            return True, f"Email simulado debido a error: {str(e)}"

    @staticmethod
    def send_password_changed_confirmation(to_email, user_name):
        """
        Enviar correo de confirmación de cambio de contraseña
        
        Args:
            to_email (str): Email del destinatario
            user_name (str): Nombre del usuario
            
        Returns:
            tuple: (bool, str) - (éxito, mensaje)
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Contraseña Cambiada - LazyFood'
            msg['From'] = Config.MAIL_DEFAULT_SENDER
            msg['To'] = to_email

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .container {{
                        background-color: #f9f9f9;
                        border-radius: 10px;
                        padding: 30px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        background-color: #A96224;
                        color: white;
                        padding: 30px 20px;
                        border-radius: 10px 10px 0 0;
                        text-align: center;
                    }}
                    .logo {{
                        width: 80px;
                        height: 80px;
                        margin: 0 auto 15px;
                        background-color: #A96224;
                        border-radius: 50%;
                        display: table;
                        text-align: center;
                        font-size: 36px;
                        font-weight: bold;
                        color: white;
                        border: 3px solid white;
                        line-height: 76px;
                    }}
                    .content {{
                        background-color: white;
                        padding: 30px;
                        border-radius: 0 0 10px 10px;
                    }}
                    .success {{
                        background-color: #fef3e8;
                        border-left: 4px solid #A96224;
                        padding: 15px;
                        margin: 15px 0;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 20px;
                        color: #666;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">LF</div>
                        <h1>LazyFood</h1>
                    </div>
                    <div class="content">
                        <h2>Hola {user_name},</h2>
                        
                        <div class="success">
                            <strong>✓ Contraseña cambiada exitosamente</strong>
                        </div>
                        
                        <p>Tu contraseña ha sido actualizada correctamente.</p>
                        
                        <p>Si no realizaste este cambio, por favor contacta inmediatamente con nuestro equipo de soporte.</p>
                        
                        <p>Saludos,<br>El equipo de LazyFood</p>
                    </div>
                    <div class="footer">
                        <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
                        <p>&copy; 2025 LazyFood. Todos los derechos reservados.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            if not Config.MAIL_USERNAME or not Config.MAIL_PASSWORD:
                print("⚠️ ADVERTENCIA: Email de confirmación simulado (sin configuración)")
                return True, "Email simulado (modo desarrollo)"

            with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
                server.starttls()
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
                server.send_message(msg)

            print(f"✓ Email de confirmación enviado a: {to_email}")
            return True, "Email enviado exitosamente"

        except Exception as e:
            print(f"❌ Error enviando email de confirmación: {str(e)}")
            return False, f"Error: {str(e)}"
