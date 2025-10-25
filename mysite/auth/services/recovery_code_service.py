"""Recovery Code Export Service"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from django.utils import timezone
import io


class RecoveryCodeService:
    """Handle recovery code export"""
    
    @staticmethod
    def export_as_txt(user, recovery_codes: list) -> str:
        """Export recovery codes as plain text
        
        Args:
            user: User object
            recovery_codes: List of plain text recovery code strings
        """
        lines = [
            "Tinybeans Recovery Codes",
            "=" * 50,
            f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"User: {user.display_name}",
            "",
            "Keep these codes in a safe place. Each code can only be used once.",
            "",
        ]
        
        for i, code in enumerate(recovery_codes, 1):
            lines.append(f"{i:2d}. {code}")
        
        lines.extend([
            "",
            "IMPORTANT:",
            "- Store these codes securely",
            "- Each code works only once",
            "- Generate new codes if these are lost",
            "- Contact support if you need help",
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def export_as_pdf(user, recovery_codes: list) -> bytes:
        """Export recovery codes as PDF
        
        Args:
            user: User object
            recovery_codes: List of plain text recovery code strings
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = Paragraph("Tinybeans Recovery Codes", styles['Heading1'])
        story.append(title)
        story.append(Spacer(1, 0.3*inch))
        
        # Info
        info_text = f"""
        <b>Generated:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}<br/>
        <b>User:</b> {user.display_name}<br/>
        <br/>
        Keep these codes in a safe place. Each code can only be used once.
        """
        info = Paragraph(info_text, styles['Normal'])
        story.append(info)
        story.append(Spacer(1, 0.5*inch))
        
        # Recovery codes table
        data = [['#', 'Recovery Code']]
        for i, code in enumerate(recovery_codes, 1):
            data.append([str(i), code])
        
        table = Table(data, colWidths=[0.5*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Courier'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.5*inch))
        
        # Important notes
        notes = Paragraph("""
        <b>IMPORTANT:</b><br/>
        • Store these codes securely (password manager, safe, etc.)<br/>
        • Each code works only once<br/>
        • Generate new codes if these are lost<br/>
        • Contact support if you need help<br/>
        """, styles['Normal'])
        story.append(notes)
        
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
