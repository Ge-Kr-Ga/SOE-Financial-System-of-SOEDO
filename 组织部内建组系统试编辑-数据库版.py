import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from models import Session, Record
import oss2  # 导入阿里云OSS SDK

# API KEY
# sk-11bd18dc8bb741509df1863d9eee9be5
# 定义文件路径
CSV_FILE = "ZZB_records.csv"
PASSWORD_FILE = "ZZB_password.txt"

# 阿里云OSS配置
OSS_ACCESS_KEY_ID = os.environ['OSS_ACCESS_KEY_ID']
OSS_ACCESS_KEY_SECRET = os.environ['OSS_ACCESS_KEY_SECRET']
OSS_BUCKET_NAME = 'financial-system-of-soedo'
OSS_ENDPOINT = 'oss-cn-shanghai.aliyuncs.com' 

# 创建OSS认证
auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

# 初始化 CSV 文件（如果文件不存在）
if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=['姓名', '部门', '上传项目', '金额', '材料分类', '操作时间', 'PDF文件路径', '备注']).to_csv(CSV_FILE, index=False)

# 初始化密码文件（如果文件不存在）
if not os.path.exists(PASSWORD_FILE):
    with open(PASSWORD_FILE, "w") as f:
        f.write("123456")  # 默认密码

# 创建数据库引擎
engine = create_engine('sqlite:///ZZB_records.db')
Base = declarative_base()


class Record(Base):
    __tablename__ = 'records'
    
    id = Column(String, primary_key=True)
    name = Column(String)
    department = Column(String)
    item = Column(String)
    amount = Column(Float)
    pdf_path = Column(Text)
    remarks = Column(Text)
    category = Column(String)
    operation_time = Column(String)  # 新增操作时间列

Base.metadata.create_all(engine)

# 创建会话
Session = sessionmaker(bind=engine)

# 从数据库加载数据
def load_data():
    session = Session()
    records = session.query(Record).all()
    return pd.DataFrame([(r.name, r.department, r.item, r.amount, r.category, r.operation_time, r.pdf_path, r.remarks) for r in records],
                        columns=['姓名', '部门', '上传项目', '金额', '材料分类', '操作时间', 'PDF文件路径', '备注'])

# 将数据保存到数据库
def save_data(df):
    session = Session()
    # 清空表格
    session.query(Record).delete()
    for index, row in df.iterrows():
        record = Record(
            id=str(index),  # 或者使用其他唯一标识符
            name=row['姓名'],
            department=row['部门'],
            item=row['上传项目'],
            amount=row['金额'],
            pdf_path=row['PDF文件路径'],
            remarks=row['备注'],
            category=row['材料分类'],
            operation_time=row['操作时间']  # 保存操作时间
        )
        session.add(record)
    session.commit()

# 导出数据为 Excel 文件
def export_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="上传记录")
    output.seek(0)
    return output

# 获取当前密码
def get_password():
    with open(PASSWORD_FILE, "r") as f:
        return f.read().strip()

# 设置新密码
def set_password(new_password):
    with open(PASSWORD_FILE, "w") as f:
        f.write(new_password)

# 页面1: 输入界面
def input_page():
    st.title("经组财务报销网站")
    st.write('当前版本：**20250313**')
    st.write('材料提交说明：每份报销需要提交至少四份材料：发票、支付截图、商品明细、活动人员名单')
    st.write('发票：注意发票应开**企业发票而非个人发票**，企业名称为**复旦大学**，税号：**12100000425006117P**。最好选择**商品大类**开发票，其次选择**商品明细**;')
    st.write('支付截图：指使用支付宝、微信、云闪付等软件支付的凭证，可打开对应软件在**历史账单**中查询。如果是现金支付，则需要拍摄小票或收据上的支付金额信息；')
    st.write('商品明细：指购买商品的清单。可以是购物软件的订单截图（含商品明细），也可以是网购到货后包裹中的纸质购货清单，或线下购物打印的小票；')
    st.write('活动人员名单：指该发票对应活动的参与人员名单，需采用**excel形式**,表格内部**每个姓名占据一个单元格**，其他样式不限。要注意支出与人数匹配，本张发票金额/活动参与人数**≤20**为宜.')

    
    # 初始化会话状态
    if 'show_edit_form' not in st.session_state:
        st.session_state.show_edit_form = False
    if 'edit_record_index' not in st.session_state:
        st.session_state.edit_record_index = None
    if 'uploaded_pdf_path' not in st.session_state:
        st.session_state.uploaded_pdf_path = None

    with st.form("input_form"):
        name = st.text_input("上报人姓名", key="surname_input")
        selected_department = st.radio(
            "选择部门",
            options=["团校", "团务", "创宣", "内建"],
            key="department_radio",
            horizontal=True
        )
        selected_category = st.radio(
            "选择材料分类",
            options=["发票", "支付截图", "商品明细", "活动人员名单"],
            key="category_radio",
            horizontal=True
        )
        # 在这里插入以下文本，并用小粗体注明中括号中字体：
        # 发票：注意发票应开【企业发票而非个人发票】，企业名称为【复旦大学】，税号：【12100000425006117P】。（换行）
        # 支付截图：指使用支付宝、微信、云闪付等软件支付的凭证，可打开对应软件在【历史账单】中查询（如图，插入一张本地图片）；商品明细
        item = st.text_input("该发票对应活动名称")
        amount = st.number_input("报销金额", min_value=0.0, format="%.2f")
        remarks = st.text_area("备注", "", key="remarks_input")
        uploaded_file = st.file_uploader(
            "上传文件（支持PDF、图片和Excel格式）", 
            type=['pdf', 'png', 'jpg', 'jpeg', 'xlsx', 'xls'], 
            help="请上传PDF文件、图片文件（支持PNG、JPG格式）或Excel文件（支持xlsx、xls格式）"
        )
        operation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
        submitted = st.form_submit_button("提交")
        
        if submitted:
            if not name or not item:
                st.error("姓名和上传项目不能为空！")
            elif amount <= 0:
                st.error("金额必须大于0！")
            else:
                pdf_path = None
                if uploaded_file is not None:
                    try:
                        # 上传文件到阿里云OSS
                        subfolder = os.path.join('uploaded_pdfs', selected_category)
                        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
                        base_filename = f"{name}-{item}-{selected_category}"
                        filename = base_filename + file_extension
                        pdf_path = os.path.join(subfolder, filename)
                        counter = 1
                        while os.path.exists(pdf_path):
                            filename = f"{base_filename}_{counter}{file_extension}"
                            pdf_path = os.path.join(subfolder, filename)
                            counter += 1
                        
                        # 上传到OSS
                        bucket.put_object(pdf_path, uploaded_file.read())
                        
                        st.success("文件上传成功！")
                        
                    except Exception as e:
                        st.error(f"文件处理失败：{str(e)}")
                        return

                df = load_data()
                existing_record = df[(df['上传项目'] == item) & (df['材料分类'] == selected_category)]

                if not existing_record.empty:
                    st.warning("此活动的该材料已经存在！")
                    st.session_state.show_edit_form = True
                    st.session_state.edit_record_index = existing_record.index[0]
                else:
                    # 新增记录
                    new_record = pd.DataFrame([[name, selected_department, item, amount, selected_category, operation_time, pdf_path, remarks]], 
                                           columns=['姓名', '部门', '上传项目', '金额', '材料分类', '操作时间', 'PDF文件路径', '备注'])
                    df = pd.concat([df, new_record], ignore_index=True)
                    save_data(df)
                    st.success("上传记录已添加！")

    if st.session_state.show_edit_form:
        st.write("修改报销金额：")
        with st.form("edit_form"):
            df = load_data()
            record_index = st.session_state.edit_record_index
            new_amount = st.number_input("修改报销金额", value=df.loc[record_index, '金额'], min_value=0.0, format="%.2f")
            new_remarks = st.text_area("新增备注", key="edit_remarks_input")
            submit_button = st.form_submit_button("保存修改")
            if submit_button:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                modified_note = f"已修改{current_time}，{new_remarks}"
                if df.loc[record_index, '备注']:
                    df.loc[record_index, '备注'] += " 丨 " + modified_note
                else:
                    df.loc[record_index, '备注'] = modified_note

                df.loc[record_index, '金额'] = new_amount
                df.loc[record_index, '备注'] = df.loc[record_index, '备注']
                save_data(df)
                st.success("金额已修改！")
                st.session_state.show_edit_form = False
                st.session_state.edit_record_index = None

# 页面2: 明细页面（需要密码）
def details_page():
    st.title("账本中心")
    
    password = st.text_input("请输入密码", type="password")
    if st.button("验证密码"):
        if password == get_password():
            st.session_state["authenticated"] = True
            st.success("密码正确！")
        else:
            st.error("密码错误，无法访问！")
    
    if st.session_state.get("authenticated", False):
        df = load_data()
        st.write("所有上传明细：")
        st.dataframe(df)

        # 删除记录功能
        record_to_delete = st.selectbox("选择要删除的记录", df.index, format_func=lambda x: f"{df.loc[x, '姓名']} - {df.loc[x, '上传项目']}")
        if st.button("删除记录"):
            if st.session_state.get("authenticated", False):
                # 获取要删除的记录信息
                pdf_path_to_delete = df.loc[record_to_delete, 'PDF文件路径']
                
                # 从数据库中删除记录
                session = Session()
                session.query(Record).filter(Record.id == str(record_to_delete)).delete()
                session.commit()
                
                # 从 CSV 文件中删除记录
                df = df.drop(record_to_delete).reset_index(drop=True)
                df.to_csv(CSV_FILE, index=False)
                
                # 从阿里云OSS中删除文件
                bucket.delete_object(pdf_path_to_delete)
                
                st.success("记录已删除！")
            else:
                st.error("请先验证密码！")

        st.write("### 筛选")
        if 'filter_type' not in st.session_state:
            st.session_state.filter_type = None
        if 'show_filter' not in st.session_state:
            st.session_state.show_filter = False

        filter_choice = st.radio(
            "选择筛选方式",
            ["按材料分类筛选", "按上传项目筛选", "按姓名筛选", "按部门筛选"],
            key="filter_radio"
        )

        if filter_choice == "按部门筛选":
            departments = df["部门"].unique()
            selected_value = st.selectbox("选择部门", departments)
            
            if st.button("确定筛选", key="confirm_filter"):
                filtered_df = df[df["部门"] == selected_value]
                st.write(f"显示 {selected_value} 部门的上传记录：")
                st.dataframe(filtered_df)

        elif filter_choice == "按材料分类筛选":
            categories = df["材料分类"].unique()
            selected_value = st.selectbox("选择材料分类", categories)
            
            if st.button("确定筛选", key="confirm_filter"):
                filtered_df = df[df["材料分类"] == selected_value]
                st.write(f"显示材料分类为 {selected_value} 的上传记录：")
                st.dataframe(filtered_df)

        elif filter_choice == "按上传项目筛选":
            payment_projects = df["上传项目"].unique()
            selected_value = st.selectbox("选择上传项目", payment_projects)
            
            if st.button("确定筛选", key="confirm_filter"):
                filtered_df = df[df["上传项目"] == selected_value]
                st.write(f"显示 {selected_value} 的上传记录：")
                st.dataframe(filtered_df)

        elif filter_choice == "按姓名筛选":
            customer_names = df["姓名"].unique()
            selected_value = st.radio("选择姓名", customer_names)
            
            if st.button("确定筛选", key="confirm_filter"):
                filtered_df = df[df["姓名"] == selected_value]
                st.write(f"显示姓名为 {selected_value} 的上传记录：")
                st.dataframe(filtered_df)

        default_name = f"records_{datetime.now().strftime('%Y%m%d_%H%M')}"
        file_name = st.text_input("请输入导出文件名", value=default_name)
        if st.button("导出为 Excel 文件"):
            if not file_name:
                st.warning("请输入文件名！")
            else:
                excel_file = export_to_excel(df)
                st.download_button(
                    label="下载 Excel 文件",
                    data=excel_file,
                    file_name=f"{file_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# 页面3: 查询材料上传历史
def query_page():
    st.title("上传查询材料上传历史")
    
    name_to_query = st.text_input("请输入姓名")
    if st.button("查询"):
        df = load_data()
        result = df[df['姓名'] == name_to_query]
        if not result.empty:
            st.write(f"{name_to_query} 的上传记录：")
            st.dataframe(result)
        else:
            st.warning("未找到其上传记录。")

# 页面4: 密码设置页面
def password_page():
    st.title("密码设置页面")
    
    current_password = st.text_input("请输入当前密码", type="password")
    new_password = st.text_input("请输入新密码", type="password")
    confirm_password = st.text_input("请确认新密码", type="password")
    
    if st.button("设置新密码"):
        if current_password != get_password():
            st.error("当前密码错误！")
        elif new_password != confirm_password:
            st.error("新密码与确认密码不一致！")
        else:
            set_password(new_password)
            st.success("密码已更新！")

# 主页面导航
st.sidebar.title("导航")
page = st.sidebar.radio("选择页面", ["输入界面", "账本中心", "查询材料上传历史", "密码设置页面"])

if page == "输入界面":
    input_page()
elif page == "账本中心":
    details_page()
elif page == "查询材料上传历史":
    query_page()
elif page == "密码设置页面":
    password_page()