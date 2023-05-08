
import math
import os
import shutil
from xml.dom.minidom import Document

import bpy
import bpy_extras
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ExportHelper
from mathutils import Matrix

bl_info = {
    "name": "Export Nori scenes format",
    "author": "Adrien Gruson, Delio Vicini, Tizian Zeltner",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "File > Export > Nori exporter (.xml)",
    "description": "Export Nori scene format (.xml)",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"}


class NoriWriter:

    def __init__(self, context, filepath, export_texture, export_lights):
        self.context = context
        self.filepath = filepath
        self.working_dir = os.path.dirname(self.filepath)
        self.export_textures = export_texture
        self.export_lights = export_lights

    def create_xml_element(self, name, attr):
        el = self.doc.createElement(name)
        for k, v in attr.items():
            el.setAttribute(k, v)
        return el

    def create_xml_entry(self, t, name, value):
        return self.create_xml_element(t, {"name": name, "value": value})

    def create_xml_transform(self, mat, el=None):
        transform = self.create_xml_element("transform", {"name": "toWorld"})
        if(el):
            transform.appendChild(el)
        value = ""
        for j in range(4):
            for i in range(4):
                value += str(mat[j][i]) + ","
        transform.appendChild(self.create_xml_element("matrix", {"value": value[:-1]}))
        return transform

    def create_xml_mesh_entry(self, filename):
        meshElement = self.create_xml_element("mesh", {"type": "obj"})
        meshElement.appendChild(self.create_xml_element("string", {"name": "filename", "value": "meshes/"+filename}))
        return meshElement

    def create_color_texture(self, name, c):
        color_entry = self.create_xml_element("texture", {"type": "constant", "name":name})
        color_entry.appendChild(self.create_xml_entry("color", "value", f"{c[0]}, {c[1]}, {c[2]}"))
        return color_entry

    def create_xml_texture(self, name, color_socket):
        c = color_socket.default_value
        linked_nodes = color_socket.links
        color_entry = self.create_xml_entry("color", name, f"{c[0]}, {c[1]}, {c[2]}")

        if len(linked_nodes) > 0 and self.export_textures:
            if (linked_nodes[0].from_node.bl_label == "Image Texture"):
                texture = self.create_xml_entry("string",name,bpy.path.relpath(linked_nodes[0].from_node.image.filepath)[2:])
                color_entry = texture

        return color_entry

    def create_xml_bsdf(self, slot):
        """method responsible to the auto-conversion
        between Blender internal BSDF (not Cycles!) and Nori BSDF
        """

        node_tree = slot.material.node_tree

        if (node_tree is None):
            c = slot.material.diffuse_color
            bsdfElement = self.create_xml_element("bsdf", {"type":"diffuse"})
            bsdfElement.appendChild(self.create_xml_entry("color", "value", f"{c[0]}, {c[1]}, {c[2]}"))
            return bsdfElement
        nodes = node_tree.nodes

        normal = nodes.get("Normal Map")
        diffuse = nodes.get("Diffuse BSDF")
        principled = nodes.get("Principled BSDF")
        specular = nodes.get("Specular")
        glass = nodes.get("Glass BSDF")
        glossy = nodes.get("Glossy BSDF")



        #if (glass):
        #    ior = glass.inputs["IOR"].default_value
        #    bsdfElement = self.create_xml_element("bsdf", {"type":"dielectric"}) # For compatibility reasons this is not called roughdielectric
        #    bsdfElement.appendChild(self.__createColorOrTexture("color", glass.inputs["Color"]))
        #    bsdfElement.appendChild(self.create_xml_entry("float", "IOR","%f" % ior))
        #    bsdfElement.appendChild(self.create_xml_entry("float", "roughness","%f" % glass.inputs["Roughness"].default_value))
        #elif (glossy and exportMaterialColor):
        #    alpha = glossy.inputs["Roughness"].default_value
        #    bsdfElement = self.__createElement("bsdf", {"type":"microfacet", "name" : slot.material.name})
        #    bsdfElement.appendChild(self.__createColorOrTexture("kd", glossy.inputs["Color"]))
        #    bsdfElement.appendChild(self.__createEntry("float", "alpha","%f" % alpha))
        if (diffuse):
            bsdfElement = self.create_xml_element("bsdf", {"type":"diffuse"})
            bsdfElement.appendChild(self.create_xml_texture("albedo", diffuse.inputs["Color"]))
            #bsdfElement.appendChild(self.create_xml_texture("normal", diffuse.inputs["Normal"]))
        else:
            c = slot.material.diffuse_color
            bsdfElement = self.create_xml_element("bsdf", {"type":"diffuse"})
            bsdfElement.appendChild(self.create_xml_entry("color", "value", f"{c[0]}, {c[1]}, {c[2]}"))

        #elif (principled and exportMaterialColor):
        #    c = principled.inputs["Base Color"].default_value
        #    bsdfElement = self.__createElement("bsdf", {"type":"disney", "name" : slot.material.name})
        #    bsdfElement.appendChild(self.__createColorOrTexture("baseColor", principled.inputs["Base Color"]))
        #    bsdfElement.appendChild(self.__createEntry("float", "metallic","%f" %(principled.inputs["Metallic"].default_value)))
        #    bsdfElement.appendChild(self.__createEntry("float", "subsurface","%f" %(principled.inputs["Subsurface"].default_value)))
        #    bsdfElement.appendChild(self.__createEntry("float", "specular","%f" %(principled.inputs["Specular"].default_value)))
        #    bsdfElement.appendChild(self.__createEntry("float", "specularTint","%f" %(principled.inputs["Specular Tint"].default_value)))
        #    bsdfElement.appendChild(self.__createEntry("float", "roughness","%f" %(principled.inputs["Roughness"].default_value)))
        #    bsdfElement.appendChild(self.__createEntry("float", "anisotropic","%f" %(principled.inputs["Anisotropic"].default_value)))
        #    bsdfElement.appendChild(self.__createEntry("float", "sheen","%f" %(principled.inputs["Sheen"].default_value)))
        #    bsdfElement.appendChild(self.__createEntry("float", "sheenTint","%f" %(principled.inputs["Sheen Tint"].default_value)))
        #    bsdfElement.appendChild(self.__createEntry("float", "clearcoat","%f" %(principled.inputs["Clearcoat"].default_value)))
        #    bsdfElement.appendChild(self.__createEntry("float", "clearcoatGloss","%f" %(principled.inputs["Clearcoat Roughness"].default_value)))


        #elif (specular and exportMaterialColor):
        #    bsdfElement = self.__createElement("bsdf", {"type":"mirror", "name" : slot.material.name})
        #else:
        #    c = slot.material.diffuse_color
        #    bsdfElement = self.__createElement("bsdf", {"type":"diffuse", "name" : slot.material.name})
        #    bsdfElement.appendChild(self.__createEntry("color", "albedo","%f,%f,%f" %(c[0],c[1],c[2])))
        if (normal):
            baseBsdf = self.create_xml_element("bsdf", {"type":"normal"})
            baseBsdf.appendChild(self.create_xml_texture("normal", normal.inputs["Color"]))
            baseBsdf.appendChild(bsdfElement)
            return baseBsdf


        return bsdfElement

    def to_nori_coord(self, transform):
        coord_transf = bpy_extras.io_utils.axis_conversion(
            from_forward='Y', from_up='Z', to_forward='-Z', to_up='Y').to_4x4()
        return coord_transf @ transform


    def write(self, n_samples):
        """Main method to write the blender scene into Nori format"""

        # create xml document
        self.doc = Document()
        self.scene = self.doc.createElement("scene")
        self.doc.appendChild(self.scene)

        # 1) write integrator configuration
        self.scene.appendChild(self.create_xml_element("integrator", {"type": "path_mis"}))

        # 2) write sampler
        sampler = self.create_xml_element("sampler", {"type": "independent"})
        sampler.appendChild(self.create_xml_element("integer", {"name": "sampleCount", "value": str(n_samples)}))
        self.scene.appendChild(sampler)

        # 3) export one camera
        cameras = [cam for cam in self.context.scene.objects
                   if cam.type in {'CAMERA'}]
        if(len(cameras) == 0):
            print("WARN: No camera to export")
        else:
            if(len(cameras) > 1):
                print("WARN: Does not handle multiple camera, only export the active one")
            self.scene.appendChild(self.write_camera(self.context.scene.camera))  # export the active one

        # 4) export lights
        if(self.export_lights):
            sources = [obj for obj in self.context.scene.objects
                          if obj.type in {'LIGHT'} and obj.visible_get()]
            for source in sources:
                if(source.data.type == "POINT"):
                    pointLight = self.create_xml_element("emitter", {"type" : "point" })
                    pos = self.to_nori_coord(source.matrix_world).translation

                    pointLight.appendChild(self.create_xml_entry("point", "position", "%f,%f,%f"%(pos.x,pos.y,pos.z)))
                    power = source.data.energy
                    color = list(source.data.color).copy()
                    pointLight.appendChild(self.create_xml_entry("color", "color", f"{color[0]}, {color[1]}, {color[2]}"))
                    pointLight.appendChild(self.create_xml_entry("float", "power", str(power)))
                    self.scene.appendChild(pointLight)

        # 5) export all meshes
        if not os.path.exists(self.working_dir + "/meshes"):
            os.makedirs(self.working_dir + "/meshes")

        meshes = [obj for obj in self.context.scene.objects
                  if obj.type in {'MESH', 'FONT', 'SURFACE', 'META'}]

        for mesh in meshes:
            if mesh.visible_get():
                self.write_mesh(mesh)

        # 6) write the xml file
        self.doc.writexml(open(self.filepath, "w"), "", "\t", "\n")

    def write_camera(self, cam):
        """convert the selected camera (cam) into xml format"""
        camera = self.create_xml_element("camera", {"type": "perspective"})
        camera.appendChild(self.create_xml_entry("float", "fov", str(cam.data.angle * 180 / math.pi)))
        camera.appendChild(self.create_xml_entry("float", "nearClip", str(cam.data.clip_start)))
        camera.appendChild(self.create_xml_entry("float", "farClip", str(cam.data.clip_end)))
        percent = self.context.scene.render.resolution_percentage / 100.0
        camera.appendChild(self.create_xml_entry("integer", "width", str(
            int(self.context.scene.render.resolution_x * percent))))
        camera.appendChild(self.create_xml_entry("integer", "height", str(
            int(self.context.scene.render.resolution_y * percent))))

        mat = cam.matrix_world

        # Conversion to Y-up coordinate system
        coord_transf = bpy_extras.io_utils.axis_conversion(
            from_forward='Y', from_up='Z', to_forward='-Z', to_up='Y').to_4x4()
        mat = coord_transf @ mat
        pos = mat.translation
        # Nori's camera needs this these coordinates to be flipped
        m = Matrix([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 0]])
        t = mat.to_3x3() @ m.to_3x3()
        mat = Matrix([[t[0][0], t[0][1], t[0][2], pos[0]],
                      [t[1][0], t[1][1], t[1][2], pos[1]],
                      [t[2][0], t[2][1], t[2][2], pos[2]],
                      [0, 0, 0, 1]])
        trans = self.create_xml_transform(mat)
        camera.appendChild(trans)
        return camera

    def write_mesh(self, mesh):
        viewport_selection = self.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')

        obj_name = mesh.name + ".obj"
        obj_path = os.path.join(self.working_dir, 'meshes', obj_name)
        mesh.select_set(True)
        bpy.ops.export_scene.obj(filepath=obj_path, check_existing=False,
                                    use_selection=True, use_edges=False, use_smooth_groups=False,
                                    use_materials=False, use_triangles=True, use_mesh_modifiers=True)

        haveMaterial = (len(mesh.material_slots) != 0 and mesh.material_slots[0].name != '')
        mesh.select_set(False)

        # Add the corresponding entry to the xml
        mesh_element = self.create_xml_mesh_entry(obj_name)

        if(not haveMaterial):
            # add default BSDF
            bsdf_element = self.create_xml_element("bsdf", {"type": "diffuse"})
            bsdf_element.appendChild(self.create_xml_entry("color", "albedo", "0.75,0.75,0.75"))
            mesh_element.appendChild(bsdf_element)
            self.scene.appendChild(mesh_element)        
        else:
            for id_mat in range(len(mesh.material_slots)):
                slot = mesh.material_slots[id_mat]
                # We create xml related entry
                mesh_element.appendChild(self.create_xml_bsdf(slot))
                # Check for emissive surfaces
                node_tree = slot.material.node_tree

                if (node_tree is None):
                    continue
                nodes = node_tree.nodes
                emission = nodes.get("Emission")

                if (emission and self.export_lights):
                    strength = emission.inputs["Strength"].default_value

                    areaLight = self.create_xml_element("emitter", {"type" : "area" })
                    areaLight.appendChild(self.create_xml_texture("radiance", emission.inputs["Color"]))
                    areaLight.appendChild(self.create_xml_entry("float", "strength", str(strength)))
                    mesh_element.appendChild(areaLight)

                self.scene.appendChild(mesh_element)

        for ob in viewport_selection:
            ob.select_set(True)


class NoriExporter(bpy.types.Operator, ExportHelper):
    """Export a blender scene into Nori scene format"""

    # add to menu
    bl_idname = "export_scene.nori"
    bl_label = "Export Nori scene"

    filename_ext = ".xml"
    filter_glob: StringProperty(default="*.xml", options={'HIDDEN'})

    ###################
    # other options
    ###################

    export_lights : BoolProperty(
                    name="Export Lights",
                    description="Export light to Nori",
                    default=True)

    export_material_colors : BoolProperty(
                    name="Export BSDF properties",
                    description="Export material colors instead of viewport colors",
                    default=True)
    
    export_textures : BoolProperty(
                    name="Export Textures",
                    description="Export texture connected to color socket of the material. Only effective \
                     when 'Export BSDF properties' is selected.",
                    default=True)

    export_meshes_in_world : BoolProperty(
                    name="Export OBJ in world coords",
                    description="Export meshes in world coordinate frame.",
                    default=False)
    
    export_meshes_triangular : BoolProperty(
                    name="Triangular Mesh",
                    description="Convert faces to triangles.",
                    default=False)

    nb_samples : IntProperty(name="Numbers of camera rays",
                    description="Number of camera ray",
                    default=32)

    def execute(self, context):
        nori = NoriWriter(context, self.filepath, self.export_textures, self.export_lights)
        nori.write(self.nb_samples)
        return {'FINISHED'}


def menu_func_export(self, context):
    default_path = bpy.data.filepath.replace(".blend", ".xml")
    self.layout.operator(NoriExporter.bl_idname, text="Export Nori scene...").filepath = default_path


def register():
    bpy.utils.register_class(NoriExporter)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(NoriExporter)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
