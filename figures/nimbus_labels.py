"""Use the same Nimbus Roman Type 1 faces as the IEEE manuscript."""
from io import BytesIO
import os
from pathlib import Path
import shutil
import subprocess

from matplotlib import colors, font_manager


FACES={('normal','normal'):('utmr8a','NimbusRomNo9L-Regu'),
       ('normal','bold'):('utmb8a','NimbusRomNo9L-Medi'),
       ('italic','normal'):('utmri8a','NimbusRomNo9L-ReguItal'),
       ('italic','bold'):('utmbi8a','NimbusRomNo9L-MediItal')}


def locate(name,extension):
    folder=os.environ.get('NIMBUS_ROMAN_'+extension.upper()+'_DIR')
    if folder:
        path=Path(folder)/f'{name}.{extension}'
        if path.is_file():return path
        raise FileNotFoundError(path)
    kpse=shutil.which('kpsewhich')
    if kpse:
        result=subprocess.run([kpse,f'{name}.{extension}'],capture_output=True,text=True,check=False)
        if result.returncode==0 and result.stdout.strip():
            return Path(result.stdout.strip())
    raise RuntimeError(f'Cannot find {name}.{extension}; install the TeX Nimbus Roman faces or set '
                       f'NIMBUS_ROMAN_{extension.upper()}_DIR')


def files(style='normal',weight='normal'):
    stem,name=FACES[(style,weight)]
    return locate(stem,'pfb'),locate(stem,'afm'),name


def measure_face(style,weight):
    pfb,_,name=files(style,weight)
    face=font_manager.get_font(str(pfb))
    if face.postscript_name!=name:
        raise ValueError(f'Unexpected IEEE face {face.postscript_name}, expected {name}')
    return font_manager.FontProperties(fname=str(pfb),style=style,weight=weight)


def write_exact_labels(fig,labels,path,metadata):
    """Embed original Type 1 programs, not a converted or rasterized face."""
    from pypdf import PdfReader,PdfWriter
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfgen import canvas

    names={}
    for style,weight in {('normal','normal'),*((a.get_fontstyle(),a.get_fontweight()) for a in labels)}:
        pfb,afm,name=files(style,weight)
        if name not in pdfmetrics.getRegisteredFontNames():
            face=pdfmetrics.EmbeddedType1Face(str(afm),str(pfb))
            if face.name!=name:
                raise ValueError(f'Unexpected AFM face {face.name}')
            pdfmetrics.registerTypeFace(face)
            pdfmetrics.registerFont(pdfmetrics.Font(name,name,'WinAnsiEncoding'))
        names[(style,weight)]=name

    w,h=(float(v)*72 for v in fig.get_size_inches())
    layer=BytesIO()
    out=canvas.Canvas(layer,pagesize=(w,h),invariant=1,initialFontName=names[('normal','normal')])
    renderer=fig.canvas.get_renderer()
    px_to_pt=72/fig.dpi
    for label in labels:
        s=label.get_text()
        if not s.isascii() or '$' in s:
            raise ValueError(f'Use literal label text with the IEEE Type 1 encoding: {s}')
        xy=label.get_transform().transform(label.get_position())
        face=names[(label.get_fontstyle(),label.get_fontweight())]
        out.setFont(face,label.get_fontsize())
        out.setFillColorRGB(*colors.to_rgb(label.get_color()))
        # Matplotlib determines text alignment using the very same original PFB.
        _,lines,_=label._get_layout(renderer)
        for line,_,*offset in lines:
            dx,dy=offset[0] if len(offset)==1 else offset
            out.drawString((xy[0]+dx)*px_to_pt,(xy[1]+dy)*px_to_pt,line)
        label.set_visible(False)
    out.save()
    geometry=BytesIO()
    fig.savefig(geometry,format='pdf',metadata=metadata)
    reader=PdfReader(geometry)
    writer=PdfWriter()
    page=writer.add_page(reader.pages[0])
    page.merge_page(PdfReader(layer).pages[0])
    writer.add_metadata({'/Creator':'Python Matplotlib and ReportLab'})
    with Path(path).open('wb') as output:
        writer.write(output)
