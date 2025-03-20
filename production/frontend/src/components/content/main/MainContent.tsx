import React from "react";
import CodeEditor from "../../editor/CodeEditor";

const MainContent: React.FC = () => {
  return (
    <CodeEditor
      value=""
      onChange={(value) => console.log(value)}
      height={300}
    />
  );
};

export default MainContent;