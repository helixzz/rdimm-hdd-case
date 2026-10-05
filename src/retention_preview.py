"""Mesh-derived views for the v2 retention retrofit. No illustrative geometry."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def preview(out,parts,assembled,screws,meshof,box,opposite,plates):
    im=Image.new('RGB',(1500,1050),'#f4f6f8')
    draw=ImageDraw.Draw(im)
    font=ImageFont.load_default(size=26)
    small=ImageFont.load_default(size=20)
    projection=np.array([[.78,-.63,0],[.33,.41,-.85],[.535,.665,.519]])

    def render(items,cx,cy,scale,center):
        pixels=np.asarray(im).copy()
        depth=np.full((im.height,im.width),-np.inf)
        for solid,color in items:
            mesh=meshof(solid)
            p=(mesh.vertices-np.asarray(center))@projection.T
            xy=p[:,:2]*scale+[cx,cy]
            for i,tri in enumerate(mesh.faces):
                normal=mesh.face_normals[i]
                if normal@projection[2]<=0:continue
                poly=xy[tri];zz=p[tri,2]
                xmin=max(0,int(np.floor(poly[:,0].min())));xmax=min(im.width-1,int(np.ceil(poly[:,0].max())))
                ymin=max(0,int(np.floor(poly[:,1].min())));ymax=min(im.height-1,int(np.ceil(poly[:,1].max())))
                if xmin>xmax or ymin>ymax:continue
                xx,yy=np.meshgrid(np.arange(xmin,xmax+1)+.5,np.arange(ymin,ymax+1)+.5)
                (x0,y0),(x1,y1),(x2,y2)=poly
                den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
                if abs(den)<1e-10:continue
                a=((y1-y2)*(xx-x2)+(x2-x1)*(yy-y2))/den
                b=((y2-y0)*(xx-x2)+(x0-x2)*(yy-y2))/den
                c=1-a-b;z=a*zz[0]+b*zz[1]+c*zz[2]
                target=depth[ymin:ymax+1,xmin:xmax+1]
                hit=(a>=-1e-7)&(b>=-1e-7)&(c>=-1e-7)&(z>target)
                target[hit]=z[hit]
                shade=.74+.22*max(0,float(normal@np.array([-.3,-.4,.866])))
                pixels[ymin:ymax+1,xmin:xmax+1][hit]=(np.array(color)*shade).astype(np.uint8)
        im.paste(Image.fromarray(pixels))

    blue=(87,124,151); green=(92,145,132); gold=(209,166,91)
    draw.text((35,24),'V2-R retention retrofit - reuse the printed v2 body',font=font,fill='#172c40')
    draw.text((35,65),'8 RDIMMs | 147 x 101.6 x 26 mm | replace trays + lid; add six keepers',font=small,fill='#445566')
    draw.text((35,122),'PCB edge capture (keeper raised)',font=font,fill='#172c40')
    crop=box((13,18,14),(0,25.6,0))
    tray=parts['tray-bottom-2']^crop
    cap=(parts['keeper-2-print-2']^crop).translate((0,0,3.5))
    pcb=box((133.8,31.4,1.37),(6.6,18.9,3.))^crop
    chips=(box((129.8,31.4,2.1),(8.6,18.9,.9))+box((129.8,31.4,2.1),(8.6,18.9,4.37)))^crop
    render([(tray,green),(pcb,(83,109,67)),(chips,(55,64,71)),(cap,gold)],330,440,18,[6.5,34.6,0])
    draw.text((35,555),'Gold lip stops the blank PCB edge from lifting.',font=small,fill='#445566')
    draw.text((35,585),'Guides contact the PCB before broad cavity walls.',font=small,fill='#445566')
    draw.text((800,122),'Exploded retrofit assembly',font=font,fill='#172c40')
    items=[(assembled[0],blue)]
    for tier in range(3):
        for index in range(2+3*tier,5+3*tier):
            items.append((assembled[index].translate((0,0,25+17*tier)),green if index%3==2 else gold))
    items.append((assembled[1].translate((0,0,90)),blue))
    items.extend((s.translate((0,0,90)),(150,154,158)) for s in screws[-2:])
    render(items,1110,620,2.7,[73.5,50.8,0])
    draw.text((800,805),'Two M2 x 20 ties connect lid to the bottom tray.',font=small,fill='#445566')
    draw.text((800,835),'Original four lid screws secure it to the body.',font=small,fill='#445566')
    draw.text((35,730),'Added hardware',font=font,fill='#172c40')
    draw.text((35,774),'12 x M2 x 5 countersunk keeper screws',font=small,fill='#445566')
    draw.text((35,809),'2 x M2 x 20 countersunk tie screws',font=small,fill='#445566')
    draw.text((35,884),'First print: test-tray-1 + two test keepers.',font=font,fill='#172c40')
    draw.text((35,927),'Nominal PCB play remains 0.13-0.33 mm vertically; it is not force-clamped.',font=small,fill='#445566')
    draw.text((35,966),'Rigid translation checks only. Print tolerances, impact and thread strength need physical testing.',font=small,fill='#445566')
    im.save(out/'retention-preview.png')

    # Packing diagram uses actual exported triangle projections, not mock parts.
    im=Image.new('RGB',(1500,930),'#f4f6f8');draw=ImageDraw.Draw(im)
    draw.text((35,25),'V2-R upgrade: two P2S plates (existing body reused)',font=font,fill='#172c40')
    labels=['Plate 1: lid, bottom tray, six keepers','Plate 2: middle + top trays']
    for k,(name,meshes) in enumerate(list(plates.items())[:2]):
        left=40+750*k;top=150;scale=2.5
        draw.text((left,105),labels[k],font=small,fill='#172c40')
        draw.rectangle((left,top,left+640,top+640),fill='white',outline='#81909e',width=2)
        for i,mesh in enumerate(meshes):
            hull=mesh.vertices[:,:2]
            # Wireframe triangle edges retain all actual part details.
            color=('#93b9cc','#a4c8b4','#e8c88f')[min(i,2)]
            for tri in mesh.faces:
                p=[(left+x*scale,top+(256-y)*scale) for x,y in hull[tri]]
                draw.polygon(p,fill=color)
            center=mesh.bounds[:,:2].mean(0)
            draw.text((left+center[0]*scale-5,top+(256-center[1])*scale-10),str(i+1),font=small,fill='#172c40')
    draw.text((35,835),'All parts at Z=0, 100% scale, at least 8 mm between bounding boxes. Print by layer.',font=small,fill='#445566')
    draw.text((35,882),'Use 0.10 mm layer height for keeper lips; 0.20 mm is suitable for the other parts.',font=small,fill='#445566')
    im.save(out/'upgrade-plates.png')
